from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class MediaControls(QObject):
    """Windows System Media Transport Controls for a classic desktop HWND."""

    playRequested = Signal()
    pauseRequested = Signal()
    nextRequested = Signal()
    previousRequested = Signal()
    shuffleRequested = Signal(bool)
    repeatModeRequested = Signal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.available = False
        self.controls = None
        self.updater = None
        self._button_token = None
        self._shuffle_token = None
        self._repeat_token = None
        self._MediaPlaybackStatus = None
        self._MediaPlaybackType = None
        self._Buttons = None
        self._RepeatModes = None
        self._last_position_ms = -1
        self._hwnd = None

    def attach_window(self, hwnd: int) -> bool:
        if self.available:
            return True

        if not hwnd:
            print("[Jazzify] Windows media controls unavailable: invalid window handle")
            return False

        try:
            from winrt.windows.media import (
                MediaPlaybackAutoRepeatMode,
                MediaPlaybackStatus,
                MediaPlaybackType,
                SystemMediaTransportControlsButton,
            )
            from winrt.windows.media.interop import get_for_window

            controls = get_for_window(int(hwnd))

            self._MediaPlaybackStatus = MediaPlaybackStatus
            self._MediaPlaybackType = MediaPlaybackType
            self._Buttons = SystemMediaTransportControlsButton
            self._RepeatModes = MediaPlaybackAutoRepeatMode

            controls.is_enabled = True
            controls.is_play_enabled = True
            controls.is_pause_enabled = True
            controls.is_next_enabled = True
            controls.is_previous_enabled = True

            # These properties make Windows expose Shuffle / Repeat state and,
            # when supported by the shell surface, their corresponding controls.
            controls.shuffle_enabled = False
            controls.auto_repeat_mode = MediaPlaybackAutoRepeatMode.NONE

            self.controls = controls
            self.updater = controls.display_updater

            # Tie the Windows media identity to the same AppUserModelID used by
            # Jazzify in app.py. This gives Windows a stable app/media identity.
            try:
                self.updater.app_media_id = "Jazzify.App"
            except Exception as exc:
                print(f"[Jazzify] Could not set media app id: {exc}")

            self._button_token = controls.add_button_pressed(
                self._on_button_pressed
            )

            # These events are separate from ButtonPressed in WinRT. They are
            # specifically used for the system Shuffle and Repeat controls.
            if hasattr(controls, "add_shuffle_enabled_change_requested"):
                self._shuffle_token = controls.add_shuffle_enabled_change_requested(
                    self._on_shuffle_requested
                )

            if hasattr(controls, "add_auto_repeat_mode_change_requested"):
                self._repeat_token = controls.add_auto_repeat_mode_change_requested(
                    self._on_repeat_requested
                )

            self._hwnd = int(hwnd)
            self.available = True
            print(f"[Jazzify] Windows media controls enabled (HWND={self._hwnd})")
            return True

        except Exception as exc:
            print(f"[Jazzify] Windows media controls unavailable: {exc}")
            self.controls = None
            self.updater = None
            self.available = False
            return False

    def _on_button_pressed(self, sender, args) -> None:
        try:
            button = args.button
        except Exception as exc:
            print(f"[Jazzify] Media button read error: {exc}")
            return

        try:
            buttons = self._Buttons
            if button == buttons.PLAY:
                self.playRequested.emit()
            elif button == buttons.PAUSE:
                self.pauseRequested.emit()
            elif button == buttons.NEXT:
                self.nextRequested.emit()
            elif button == buttons.PREVIOUS:
                self.previousRequested.emit()
        except Exception as exc:
            print(f"[Jazzify] Media button handling error: {exc}")

    def _on_shuffle_requested(self, sender, args) -> None:
        try:
            requested = bool(args.requested_shuffle_enabled)
            self.shuffleRequested.emit(requested)
        except Exception as exc:
            print(f"[Jazzify] Media shuffle request error: {exc}")

    def _on_repeat_requested(self, sender, args) -> None:
        try:
            requested = args.requested_auto_repeat_mode
            requested_value = int(requested)

            # WinRT values:
            #   None = 0, Track = 1, List = 2
            # Jazzify values:
            #   Off = 0, List = 1, Track = 2
            jazzify_mode = {
                0: 0,
                1: 2,
                2: 1,
            }.get(requested_value, 0)

            self.repeatModeRequested.emit(jazzify_mode)
        except Exception as exc:
            print(f"[Jazzify] Media repeat request error: {exc}")

    def update_metadata(
        self,
        title: str,
        artist: str,
        album: str,
        artwork_path: str,
    ) -> None:
        if not self.available or self.updater is None:
            return

        try:
            self.updater.type = self._MediaPlaybackType.MUSIC
            try:
                self.updater.app_media_id = "Jazzify.App"
            except Exception:
                pass

            music = self.updater.music_properties
            music.title = title or "Jazzify"
            music.artist = artist or "Unknown artist"
            music.album_artist = artist or "Unknown artist"
            music.album_title = album or "Unknown album"

            # Keep the thumbnail optional. Metadata must never depend on it.
            if artwork_path and Path(artwork_path).is_file():
                try:
                    from winrt.windows.storage.streams import RandomAccessStreamReference
                    from winrt.windows.storage import StorageFile
                    import threading

                    path = str(Path(artwork_path).resolve())

                    def load_thumbnail() -> None:
                        try:
                            file_op = StorageFile.get_file_from_path_async(path)
                            storage_file = file_op.get()
                            thumbnail = RandomAccessStreamReference.create_from_file(
                                storage_file
                            )
                            self.updater.thumbnail = thumbnail
                            self.updater.update()
                        except Exception as thumb_exc:
                            print(
                                f"[Jazzify] Media thumbnail unavailable: {thumb_exc}"
                            )

                    threading.Thread(
                        target=load_thumbnail,
                        name="JazzifyMediaArtwork",
                        daemon=True,
                    ).start()
                except Exception as exc:
                    print(f"[Jazzify] Media thumbnail setup error: {exc}")

            self.updater.update()

        except Exception as exc:
            print(f"[Jazzify] Could not update media metadata: {exc}")

    def update_status(self, playing: bool, has_media: bool) -> None:
        if not self.available or self.controls is None:
            return

        try:
            status = (
                self._MediaPlaybackStatus.PLAYING
                if playing
                else self._MediaPlaybackStatus.PAUSED
                if has_media
                else self._MediaPlaybackStatus.STOPPED
            )
            self.controls.playback_status = status
            self.controls.is_enabled = True
            self.controls.is_play_enabled = not playing
            self.controls.is_pause_enabled = bool(playing)
            self.controls.is_next_enabled = True
            self.controls.is_previous_enabled = True
        except Exception as exc:
            print(f"[Jazzify] Could not update media status: {exc}")

    def update_modes(self, shuffle_enabled: bool, repeat_mode: int) -> None:
        if not self.available or self.controls is None:
            return

        try:
            self.controls.shuffle_enabled = bool(shuffle_enabled)

            # Jazzify:
            #   0 = Off, 1 = List, 2 = Track
            # WinRT:
            #   None = Off, List = List, Track = Track
            winrt_mode = {
                0: self._RepeatModes.NONE,
                1: self._RepeatModes.LIST,
                2: self._RepeatModes.TRACK,
            }.get(int(repeat_mode), self._RepeatModes.NONE)

            self.controls.auto_repeat_mode = winrt_mode
        except Exception as exc:
            print(f"[Jazzify] Could not update media repeat/shuffle: {exc}")

    def update_timeline(self, position_ms: int, duration_ms: int) -> None:
        if not self.available or self.controls is None or duration_ms <= 0:
            return

        if (
            self._last_position_ms >= 0
            and abs(position_ms - self._last_position_ms) < 250
        ):
            return

        self._last_position_ms = position_ms

        try:
            from winrt.windows.media import SystemMediaTransportControlsTimelineProperties

            duration_td = timedelta(milliseconds=int(duration_ms))
            position_td = timedelta(milliseconds=int(position_ms))

            timeline = SystemMediaTransportControlsTimelineProperties()
            timeline.start_time = timedelta(0)
            timeline.end_time = duration_td
            timeline.min_seek_time = timedelta(0)
            timeline.max_seek_time = duration_td
            timeline.position = position_td
            self.controls.update_timeline_properties(timeline)
        except Exception as exc:
            print(f"[Jazzify] Could not update media timeline: {exc}")

    def close(self) -> None:
        if self.controls is None:
            return

        for method_name, token_attr in (
            ("remove_button_pressed", "_button_token"),
            ("remove_shuffle_enabled_change_requested", "_shuffle_token"),
            ("remove_auto_repeat_mode_change_requested", "_repeat_token"),
        ):
            token = getattr(self, token_attr, None)
            if token is None:
                continue
            try:
                remover = getattr(self.controls, method_name, None)
                if remover is not None:
                    remover(token)
            except Exception:
                pass

        self.available = False
        self.controls = None
        self.updater = None
        self._button_token = None
        self._shuffle_token = None
        self._repeat_token = None
