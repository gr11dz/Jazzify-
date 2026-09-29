from __future__ import annotations

import math
import random
import struct
import time

from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtMultimedia import QAudioFormat, QAudioOutput, QMediaPlayer

try:
    from PySide6.QtMultimedia import QAudioBufferOutput
except ImportError:
    QAudioBufferOutput = None

from .media_controls import MediaControls


class Player(QObject):
    titleChanged = Signal(str)
    artistChanged = Signal(str)
    albumChanged = Signal(str)
    artworkChanged = Signal(str)
    pathChanged = Signal(str)
    primaryColorChanged = Signal(QColor)
    secondaryColorChanged = Signal(QColor)
    backgroundColorChanged = Signal(QColor)
    playingChanged = Signal(bool)
    positionChanged = Signal(int)
    durationChanged = Signal(int)
    volumeChanged = Signal(float)
    errorChanged = Signal(str)
    queueIndexChanged = Signal(int)
    shuffleChanged = Signal(bool)
    repeatChanged = Signal(bool)
    repeatModeChanged = Signal(int)
    waveformChanged = Signal()
    queueChanged = Signal()

    def __init__(self):
        super().__init__()

        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.9)

        self.media = QMediaPlayer(self)
        self.media.setAudioOutput(self.audio)

        self.audio_buffer_output = None
        if QAudioBufferOutput is not None:
            try:
                self.audio_buffer_output = QAudioBufferOutput(self)
                self.media.setAudioBufferOutput(self.audio_buffer_output)
                self.audio_buffer_output.audioBufferReceived.connect(
                    self._on_audio_buffer
                )
            except Exception as exc:
                print(f"[Jazzify] Audio waveform output unavailable: {exc}")
                self.audio_buffer_output = None

        self.media.playbackStateChanged.connect(self._emit_playing)
        self.media.positionChanged.connect(self._on_position)
        self.media.durationChanged.connect(self._on_duration)
        self.media.errorOccurred.connect(self._on_error)
        self.media.mediaStatusChanged.connect(self._on_media_status)

        self._title = ""
        self._artist = ""
        self._album = ""
        self._artwork = ""
        self._path = ""
        self._primary_color = QColor("#9B8CFF")
        self._secondary_color = QColor("#5F6FFF")
        self._background_color = QColor("#090A0F")
        self._error = ""
        self._waveform = [0.08] * 64
        self._waveform_enabled = False
        self._waveform_dirty = False
        self._waveform_update_timer = QTimer(self)
        # 20 FPS is enough for a smooth visualizer while leaving substantially
        # more CPU headroom for games and other foreground applications.
        self._waveform_update_timer.setInterval(66)
        self._last_waveform_sample = 0.0
        self._waveform_update_timer.timeout.connect(self._flush_waveform)

        self._queue: list[dict] = []
        self._queue_index = -1
        self._shuffle = False
        self._repeat_mode = 0
        self._shuffle_order: list[int] = []
        self._shuffle_position = -1

        self.media_controls = MediaControls(self)
        # Route all transport commands through explicit slots on the Player's GUI thread.
        self.media_controls.playRequested.connect(self.resumePlayback, Qt.ConnectionType.QueuedConnection)
        self.media_controls.pauseRequested.connect(self.pausePlayback, Qt.ConnectionType.QueuedConnection)
        self.media_controls.nextRequested.connect(self.next, Qt.ConnectionType.QueuedConnection)
        self.media_controls.previousRequested.connect(self.previous, Qt.ConnectionType.QueuedConnection)
        self.media_controls.shuffleRequested.connect(self._set_shuffle_from_media_controls, Qt.ConnectionType.QueuedConnection)
        self.media_controls.repeatModeRequested.connect(self._set_repeat_from_media_controls, Qt.ConnectionType.QueuedConnection)

    def initialize_media_controls(self, hwnd: int) -> bool:
        ok = self.media_controls.attach_window(hwnd)
        if ok:
            self.media_controls.update_modes(self._shuffle, self._repeat_mode)
            self.media_controls.update_status(self.playing, bool(self._path))
        return ok

    def _emit_playing(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.playingChanged.emit(playing)
        self.media_controls.update_status(playing, bool(self._path))

    def _on_position(self, position: int):
        self.positionChanged.emit(position)
        self.media_controls.update_timeline(position, self.duration)

    def _on_duration(self, duration: int):
        self.durationChanged.emit(duration)
        self.media_controls.update_timeline(self.position, duration)

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._repeat_mode == 2:
                self._start_current()
            else:
                self.next()

    def _on_error(self, error, error_string: str):
        if not error_string:
            error_string = f"QMediaPlayer error: {error}"
        self._error = error_string
        print(f"[Jazzify Player] {error_string}")
        self.errorChanged.emit(error_string)

    @Slot(bool)
    def setWaveformEnabled(self, enabled: bool):
        """Enable waveform decoding only while Now Playing is visible and the app is focused.

        Detaching QAudioBufferOutput is important for CPU usage: simply ignoring
        received buffers would still make Qt decode/copy those buffers.
        """
        enabled = bool(enabled)
        if enabled == self._waveform_enabled:
            return

        self._waveform_enabled = enabled
        self._waveform_dirty = False

        if not enabled:
            try:
                self._waveform_update_timer.stop()
            except Exception:
                pass
            try:
                self.media.setAudioBufferOutput(None)
            except Exception:
                # Some Qt builds may not accept None; in that case we still gate
                # all processing so visualization CPU work falls to zero.
                pass
            return

        if self.audio_buffer_output is not None:
            try:
                self.media.setAudioBufferOutput(self.audio_buffer_output)
            except Exception:
                pass
        self._waveform_update_timer.start()

    @Slot()
    def _flush_waveform(self):
        if not self._waveform_enabled or not self._waveform_dirty:
            return
        self._waveform_dirty = False
        self.waveformChanged.emit()

    def _on_audio_buffer(self, buffer):
        if not self._waveform_enabled:
            return

        # The visualizer only needs a fresh shape ~16 FPS. Keeping the decode
        # callback lightweight is much cheaper than processing every buffer at
        # the native audio cadence.
        now = time.monotonic()
        if now - self._last_waveform_sample < 0.060:
            return
        self._last_waveform_sample = now

        try:
            if not buffer.isValid() or buffer.byteCount() <= 0:
                return

            fmt = buffer.format()
            channels = max(1, fmt.channelCount())
            frame_count = max(1, buffer.frameCount())
            sample_format = fmt.sampleFormat()
            raw = bytes(buffer.constData())

            # Cast the PCM bytes once instead of slicing/unpacking every sample.
            # This considerably reduces Python overhead while retaining the same
            # visual information.
            if sample_format == QAudioFormat.SampleFormat.Float:
                values = memoryview(raw).cast("f")
                scale = 1.0
                minimum = -1.0
                maximum = 1.0
            elif sample_format == QAudioFormat.SampleFormat.Int16:
                values = memoryview(raw).cast("h")
                scale = 1.0 / 32768.0
                minimum = -32768
                maximum = 32767
            elif sample_format == QAudioFormat.SampleFormat.Int32:
                values = memoryview(raw).cast("i")
                scale = 1.0 / 2147483648.0
                minimum = -2147483648
                maximum = 2147483647
            elif sample_format == QAudioFormat.SampleFormat.UInt8:
                values = raw
                scale = 1.0 / 128.0
                minimum = 0
                maximum = 255
            else:
                return

            available_frames = min(frame_count, len(values) // channels)
            if available_frames <= 0:
                return

            bins = 16
            frames_per_bin = max(1, available_frames // bins)
            sample_stride = max(1, frames_per_bin // 3)
            new_values = []

            for i in range(bins):
                start_frame = i * frames_per_bin
                end_frame = min(available_frames, (i + 1) * frames_per_bin)
                if start_frame >= end_frame:
                    new_values.append(0.02)
                    continue

                peak = 0.0
                frame = start_frame
                while frame < end_frame:
                    base = frame * channels
                    # Mono is enough for a visualizer and avoids doing the same
                    # work twice for normal stereo music. Use the louder channel.
                    for channel in range(channels):
                        sample = values[base + channel]
                        if sample_format == QAudioFormat.SampleFormat.UInt8:
                            sample = (sample - 128) * scale
                        else:
                            sample = sample * scale
                        magnitude = abs(sample)
                        if magnitude > peak:
                            peak = magnitude
                    frame += sample_stride

                
                # Keep waveform amplitude independent of the system volume.
                new_values.append(max(0.02, min(1.0, peak)))

            previous = self._waveform
            if len(previous) != 16:
                previous = [0.08] * 16

            self._waveform = [
                max(old * 0.35, incoming * 0.65)
                for old, incoming in zip(previous, new_values)
            ]
            self._waveform_dirty = True
        except Exception:
            # Visualization must never interfere with playback.
            pass

    @Property(str, notify=titleChanged)
    def title(self):
        return self._title

    @Property(str, notify=artistChanged)
    def artist(self):
        return self._artist

    @Property(str, notify=albumChanged)
    def album(self):
        return self._album

    @Property(str, notify=artworkChanged)
    def artwork(self):
        return self._artwork

    @Property(str, notify=pathChanged)
    def path(self):
        return self._path

    @Property(QColor, notify=primaryColorChanged)
    def primaryColor(self):
        return self._primary_color

    @Property(QColor, notify=secondaryColorChanged)
    def secondaryColor(self):
        return self._secondary_color

    @Property(QColor, notify=backgroundColorChanged)
    def backgroundColor(self):
        return self._background_color

    @Property(str, notify=errorChanged)
    def error(self):
        return self._error

    @Property(bool, notify=playingChanged)
    def playing(self):
        state_attr = getattr(self.media, "playbackState", None)
        state = state_attr() if callable(state_attr) else state_attr
        return state == QMediaPlayer.PlaybackState.PlayingState

    @Property(int, notify=positionChanged)
    def position(self):
        return self.media.position()

    @Property(int, notify=durationChanged)
    def duration(self):
        return self.media.duration()

    @Property(float, notify=volumeChanged)
    def volume(self):
        return self.audio.volume()

    @Property(int, notify=queueIndexChanged)
    def queueIndex(self):
        return self._queue_index

    @Property(bool, notify=shuffleChanged)
    def shuffle(self):
        return self._shuffle

    @Property(bool, notify=repeatChanged)
    def repeat(self):
        return self._repeat_mode != 0

    @Property(int, notify=repeatModeChanged)
    def repeatMode(self):
        return self._repeat_mode

    @Property(list, notify=waveformChanged)
    def waveform(self):
        return self._waveform

    def _queue_display_indices(self):
        """Return source queue indices in the order the user will hear them next."""
        if not self._queue:
            return []

        if self._shuffle:
            order = list(self._shuffle_order)
            if not order:
                return []
            start = self._shuffle_position + 1 if self._shuffle_position >= 0 else 0
            return order[start:]

        start = self._queue_index + 1 if self._queue_index >= 0 else 0
        return list(range(start, len(self._queue)))

    @Property(list, notify=queueChanged)
    def queueItems(self):
        items = []
        for display_index, source_index in enumerate(self._queue_display_indices()):
            if 0 <= source_index < len(self._queue):
                song = self._queue[source_index]
                items.append({
                    "queueIndex": source_index,
                    "displayIndex": display_index,
                    "title": str(song.get("title", "") or "Unknown"),
                    "artist": str(song.get("artist", "") or "Unknown artist"),
                    "album": str(song.get("album", "") or ""),
                    "artwork": str(song.get("artwork_path", "") or ""),
                })
        return items

    @Slot("QVariant")
    def setQueue(self, songs):
        try:
            self._queue = [dict(song) for song in (songs or [])]
        except Exception:
            self._queue = []

        self._queue_index = -1
        self._shuffle_order = []
        self._shuffle_position = -1
        self.queueIndexChanged.emit(self._queue_index)
        if self._shuffle and self._queue:
            self._build_shuffle_order()
        self.queueChanged.emit()

    @Slot("QVariant")
    def shuffleAll(self, songs):
        self.setQueue(songs)
        if not self._shuffle:
            self._shuffle = True
            self.shuffleChanged.emit(True)
        self._build_shuffle_order()
        self._shuffle_position = 0
        if self._shuffle_order:
            self._queue_index = self._shuffle_order[0]
            self._play_queue_index()

    @Slot(str, str, str, str, str, str, str, str)
    def playSong(
        self,
        path: str,
        title: str = "",
        artist: str = "",
        album: str = "",
        artwork: str = "",
        primary_color: str = "",
        secondary_color: str = "",
        background_color: str = "",
    ):
        path = str(Path(path).resolve()) if path else ""
        if not path or not Path(path).is_file():
            message = f"Audio file not found: {path}"
            print(f"[Jazzify Player] {message}")
            self._error = message
            self.errorChanged.emit(message)
            return

        self._error = ""
        self.errorChanged.emit("")

        index = self._find_index(path)
        if index >= 0:
            self._queue_index = index
            self.queueIndexChanged.emit(index)
        self.queueChanged.emit()

        self._set_metadata(
            path,
            title,
            artist,
            album,
            artwork,
            primary_color,
            secondary_color,
            background_color,
        )
        self._reset_waveform()
        self._start_current()

    def _find_index(self, path: str) -> int:
        normalized = str(Path(path).resolve()).casefold()
        for i, song in enumerate(self._queue):
            if str(song.get("path", "")).casefold() == normalized:
                return i
        return -1

    def _set_metadata(
        self,
        path: str,
        title: str,
        artist: str,
        album: str,
        artwork: str,
        primary_color: str,
        secondary_color: str,
        background_color: str,
    ):
        self._path = path
        self._title = title
        self._artist = artist
        self._album = album
        self._artwork = artwork
        self._primary_color = QColor(primary_color or "#9B8CFF")
        self._secondary_color = QColor(secondary_color or "#5F6FFF")
        self._background_color = QColor(background_color or "#090A0F")

        self.pathChanged.emit(path)
        self.titleChanged.emit(title)
        self.artistChanged.emit(artist)
        self.albumChanged.emit(album)
        self.artworkChanged.emit(artwork)
        self.primaryColorChanged.emit(self._primary_color)
        self.secondaryColorChanged.emit(self._secondary_color)
        self.backgroundColorChanged.emit(self._background_color)

        self.media_controls.update_metadata(title, artist, album, artwork)

    def _start_current(self):
        if not self._path:
            return
        print(f"[Jazzify Player] Loading: {self._path}")
        self.media.stop()
        self.media.setSource(QUrl.fromLocalFile(self._path))
        self.media.play()

    def _reset_waveform(self):
        self._waveform = [0.05] * 64
        self.waveformChanged.emit()

    def _sync_playback_state(self):
        state_attr = getattr(self.media, "playbackState", None)
        state = state_attr() if callable(state_attr) else state_attr
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.playingChanged.emit(playing)
        self.media_controls.update_status(playing, bool(self._path))

    @Slot()
    def resumePlayback(self):
        print("[Jazzify Player] resumePlayback()")
        self.media.play()
        QTimer.singleShot(0, self._sync_playback_state)

    @Slot()
    def pausePlayback(self):
        print("[Jazzify Player] pausePlayback()")
        self.media.pause()
        QTimer.singleShot(0, self._sync_playback_state)

    @Slot()
    def togglePlayback(self):
        state = self.media.playbackState() if callable(getattr(self.media, "playbackState", None)) else self.media.playbackState
        print(f"[Jazzify Player] togglePlayback() state={state}")
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.pausePlayback()
        else:
            self.resumePlayback()

    # Backwards-compatible aliases for any existing internal calls.
    @Slot()
    def play(self):
        self.resumePlayback()

    @Slot()
    def pause(self):
        self.pausePlayback()

    @Slot()
    def toggle(self):
        self.togglePlayback()

    @Slot()
    def next(self):
        if not self._queue:
            return

        if self._shuffle:
            if not self._shuffle_order:
                self._build_shuffle_order()
            self._shuffle_position += 1
            if self._shuffle_position >= len(self._shuffle_order):
                if self._repeat_mode != 0:
                    self._build_shuffle_order()
                    self._shuffle_position = 0
                else:
                    self.media.stop()
                    return
            self._queue_index = self._shuffle_order[self._shuffle_position]
        else:
            next_index = self._queue_index + 1
            if next_index >= len(self._queue):
                if self._repeat_mode == 1:
                    next_index = 0
                else:
                    self.media.stop()
                    return
            self._queue_index = next_index

        self.queueIndexChanged.emit(self._queue_index)
        self.queueChanged.emit()
        self._play_queue_index()

    @Slot()
    def previous(self):
        if not self._queue:
            return

        if self.position > 3000:
            self.seek(0)
            return

        if self._shuffle:
            if not self._shuffle_order:
                self._build_shuffle_order()
            self._shuffle_position = max(0, self._shuffle_position - 1)
            self._queue_index = self._shuffle_order[self._shuffle_position]
        else:
            previous_index = self._queue_index - 1
            if previous_index < 0:
                previous_index = len(self._queue) - 1 if self._repeat_mode == 1 else 0
            self._queue_index = previous_index

        self.queueIndexChanged.emit(self._queue_index)
        self.queueChanged.emit()
        self._play_queue_index()

    def _play_queue_index(self):
        if not 0 <= self._queue_index < len(self._queue):
            return

        song = self._queue[self._queue_index]
        self.queueIndexChanged.emit(self._queue_index)
        self.queueChanged.emit()
        self._set_metadata(
            str(song.get("path", "")),
            str(song.get("title", "")),
            str(song.get("artist", "")),
            str(song.get("album", "")),
            str(song.get("artwork_path", "")),
            str(song.get("primary_color", "")),
            str(song.get("secondary_color", "")),
            str(song.get("background_color", "")),
        )
        self._reset_waveform()
        self._start_current()

    def _build_shuffle_order(self):
        self._shuffle_order = list(range(len(self._queue)))
        random.shuffle(self._shuffle_order)
        if self._queue_index in self._shuffle_order:
            self._shuffle_position = self._shuffle_order.index(self._queue_index)
        else:
            self._shuffle_position = -1

    @Slot(int)
    def playQueueItem(self, displayIndex: int):
        upcoming = self._queue_display_indices()
        if not (0 <= displayIndex < len(upcoming)):
            return
        self._queue_index = upcoming[displayIndex]
        if self._shuffle:
            try:
                self._shuffle_position = self._shuffle_order.index(self._queue_index)
            except ValueError:
                self._shuffle_position = -1
        self.queueIndexChanged.emit(self._queue_index)
        self.queueChanged.emit()
        self._play_queue_index()

    @Slot(int, int)
    def moveQueueItem(self, fromIndex: int, toIndex: int):
        """Move an upcoming item within the visible queue order."""
        upcoming = self._queue_display_indices()
        if not (0 <= fromIndex < len(upcoming) and 0 <= toIndex < len(upcoming)):
            return
        if fromIndex == toIndex:
            return

        if self._shuffle:
            start = self._shuffle_position + 1 if self._shuffle_position >= 0 else 0
            segment_start = start
            source_pos_from = segment_start + fromIndex
            source_pos_to = segment_start + toIndex
            item = self._shuffle_order.pop(source_pos_from)
            self._shuffle_order.insert(source_pos_to, item)
        else:
            start = self._queue_index + 1 if self._queue_index >= 0 else 0
            source_from = start + fromIndex
            source_to = start + toIndex
            item = self._queue.pop(source_from)
            self._queue.insert(source_to, item)

            # Preserve the current song's source index when reordering later items.
            if self._queue_index >= start:
                self._queue_index = self._queue_index

        self.queueChanged.emit()

    @Slot(int)
    def removeQueueItem(self, displayIndex: int):
        """Remove an upcoming item from the visible queue."""
        upcoming = self._queue_display_indices()
        if not (0 <= displayIndex < len(upcoming)):
            return

        source_index = upcoming[displayIndex]

        if self._shuffle:
            try:
                self._shuffle_order.remove(source_index)
            except ValueError:
                pass
            self._queue.pop(source_index)
            self._shuffle_order = [
                idx - 1 if idx > source_index else idx
                for idx in self._shuffle_order
            ]
            if self._queue_index > source_index:
                self._queue_index -= 1
            if self._shuffle_position >= len(self._shuffle_order):
                self._shuffle_position = len(self._shuffle_order) - 1
        else:
            self._queue.pop(source_index)
            if self._queue_index > source_index:
                self._queue_index -= 1

        self.queueIndexChanged.emit(self._queue_index)
        self.queueChanged.emit()

    @Slot()
    def toggleShuffle(self):
        self._shuffle = not self._shuffle
        if self._shuffle:
            self._build_shuffle_order()
        self.shuffleChanged.emit(self._shuffle)
        self.media_controls.update_modes(self._shuffle, self._repeat_mode)

    @Slot()
    def toggleRepeat(self):
        # 0 = off, 1 = repeat list, 2 = repeat current track
        self._repeat_mode = (self._repeat_mode + 1) % 3
        self.repeatChanged.emit(self._repeat_mode != 0)
        self.repeatModeChanged.emit(self._repeat_mode)
        self.media_controls.update_modes(self._shuffle, self._repeat_mode)
        self.queueChanged.emit()

    @Slot(bool)
    def _set_shuffle_from_media_controls(self, enabled: bool):
        enabled = bool(enabled)
        if self._shuffle == enabled:
            self.media_controls.update_modes(self._shuffle, self._repeat_mode)
            return

        self._shuffle = enabled
        if self._shuffle:
            self._build_shuffle_order()
        self.shuffleChanged.emit(self._shuffle)
        self.media_controls.update_modes(self._shuffle, self._repeat_mode)

    @Slot(int)
    def _set_repeat_from_media_controls(self, mode: int):
        mode = max(0, min(2, int(mode)))
        if self._repeat_mode == mode:
            self.media_controls.update_modes(self._shuffle, self._repeat_mode)
            return

        self._repeat_mode = mode
        self.repeatChanged.emit(self._repeat_mode != 0)
        self.repeatModeChanged.emit(self._repeat_mode)
        self.media_controls.update_modes(self._shuffle, self._repeat_mode)

    @Slot()
    def stop(self):
        self.media.stop()

    @Slot(int)
    def seek(self, position: int):
        self.media.setPosition(position)

    @Slot(float)
    def setVolume(self, value: float):
        value = max(0.0, min(1.0, value))
        self.audio.setVolume(value)
        self.volumeChanged.emit(value)

    def __del__(self):
        try:
            self.media_controls.close()
        except Exception:
            pass
