from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    QRunnable,
    QThreadPool,
    Qt,
    Signal,
    Slot,
)

from .database import Database
from .indexer import Indexer
from .metadata import extract, extract_palette, is_audio
from .settings import Settings
from .watcher import Watcher


class SongModel(QAbstractListModel):
    PATH = Qt.UserRole + 1
    TITLE = Qt.UserRole + 2
    ARTIST = Qt.UserRole + 3
    ALBUM = Qt.UserRole + 4
    DURATION = Qt.UserRole + 5
    ARTWORK = Qt.UserRole + 6
    PRIMARY = Qt.UserRole + 7
    SECONDARY = Qt.UserRole + 8
    BACKGROUND = Qt.UserRole + 9

    _roles = {
        PATH: b"path",
        TITLE: b"title",
        ARTIST: b"artist",
        ALBUM: b"album",
        DURATION: b"duration",
        ARTWORK: b"artworkPath",
        PRIMARY: b"primaryColor",
        SECONDARY: b"secondaryColor",
        BACKGROUND: b"backgroundColor",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._songs: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._songs)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._songs):
            return None
        song = self._songs[index.row()]
        keys = {
            self.PATH: "path",
            self.TITLE: "title",
            self.ARTIST: "artist",
            self.ALBUM: "album",
            self.DURATION: "duration",
            self.ARTWORK: "artwork_path",
            self.PRIMARY: "primary_color",
            self.SECONDARY: "secondary_color",
            self.BACKGROUND: "background_color",
        }
        return song.get(keys.get(role, "title"), "")

    def roleNames(self):
        return self._roles

    def resetSongs(self, songs: list[dict]):
        self.beginResetModel()
        self._songs = list(songs)
        self.endResetModel()

    def replaceByPath(self, song: dict):
        for i, current in enumerate(self._songs):
            if current["path"] == song["path"]:
                self._songs[i] = song
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, list(self._roles))
                return
        self._songs.append(song)
        self._songs.sort(
            key=lambda x: (
                -(x.get("added_at") or 0),
                x.get("title", "").casefold(),
                x.get("artist", "").casefold(),
            )
        )
        self.resetSongs(self._songs)

    def removeByPath(self, path: str):
        filtered = [song for song in self._songs if song["path"] != path]
        if len(filtered) != len(self._songs):
            self.resetSongs(filtered)


class _PaletteSignals(QObject):
    ready = Signal(str, str, str, str)


class _PaletteJob(QRunnable):
    def __init__(self, path: str, artwork_path: str, signals: _PaletteSignals):
        super().__init__()
        self.path = path
        self.artwork_path = artwork_path
        self.signals = signals

    def run(self):
        try:
            from PIL import Image

            with Image.open(self.artwork_path) as image:
                palette = extract_palette(image)
            self.signals.ready.emit(self.path, *palette)
        except Exception:
            pass


class Library(QObject):
    countChanged = Signal()
    statusChanged = Signal(str)
    indexingChanged = Signal(bool)

    def __init__(self, database: Database, settings: Settings, artwork_cache: Path):
        super().__init__()
        self.database = database
        self.settings = settings
        self.artwork_cache = Path(artwork_cache)
        self.artwork_cache.mkdir(parents=True, exist_ok=True)
        self.model = SongModel(self)
        self.indexer = Indexer(self.artwork_cache)
        self.indexer.songFound.connect(self._on_song)
        self.watcher = Watcher(self)
        self.watcher.created.connect(self._index_one)
        self.watcher.modified.connect(lambda p: self._index_one(p, True))
        self.watcher.deleted.connect(self._on_deleted)
        self.palette_pool = QThreadPool(self)
        self.palette_signals = _PaletteSignals()
        self.palette_signals.ready.connect(self._palette_ready)
        self._running = False
        self._indexing = False
        self.indexer.indexStarted.connect(self._index_started)
        self.indexer.indexFinished.connect(self._index_finished)

    @Property(QObject, constant=True)
    def songsModel(self):
        return self.model

    @Property(int, notify=countChanged)
    def songCount(self):
        return self.model.rowCount()

    @Property(bool, notify=indexingChanged)
    def indexing(self) -> bool:
        return self._indexing

    @Slot()
    def _index_started(self):
        if not self._indexing:
            self._indexing = True
            self.indexingChanged.emit(True)
        self.statusChanged.emit("Indexing music library…")

    @Slot()
    def _index_finished(self):
        if self._indexing:
            self._indexing = False
            self.indexingChanged.emit(False)
        self.statusChanged.emit("Library ready")

    @Slot()
    def start(self):
        songs = self.database.songs()
        self.model.resetSongs(songs)
        self.countChanged.emit()

        folders = self.settings.music_folders
        self._running = True
        self.watcher.start(folders)

        self._backfill_palettes(songs)
        for folder in folders:
            self.indexer.index(folder)

    def _backfill_palettes(self, songs: list[dict]):
        for song in songs:
            if not song.get("artwork_path"):
                continue
            if song.get("primary_color") and song.get("background_color"):
                continue
            artwork = song["artwork_path"]
            if Path(artwork).is_file():
                self.palette_pool.start(
                    _PaletteJob(
                        song["path"],
                        artwork,
                        self.palette_signals,
                    )
                )

    @Slot(str, str, str, str)
    def _palette_ready(
        self,
        path: str,
        primary: str,
        secondary: str,
        background: str,
    ):
        self.database.update_visuals(path, primary, secondary, background)
        self.database.commit()
        row = self.database.song_by_path(path)
        if row:
            self.model.replaceByPath(dict(row))

    @Slot(str)
    def addFolder(self, folder: str):
        path = Path(folder).resolve()
        if not path.is_dir():
            self.statusChanged.emit("Folder does not exist")
            return
        text = str(path)
        folders = self.settings.music_folders
        if text not in folders:
            folders.append(text)
            self.settings.set_music_folders(folders)
            self.database.add_folder(text)
            if self._running:
                self.indexer.index(text)
                self.watcher.start(folders)
        self.statusChanged.emit(f"Indexing {text}")

    @Slot(str)
    def removeFolder(self, folder: str):
        self.database.remove_folder(folder)
        self.settings.set_music_folders(
            [f for f in self.settings.music_folders if f != folder]
        )
        self.model.resetSongs(self.database.songs())
        self.countChanged.emit()
        self.watcher.start(self.settings.music_folders)

    @Slot(result="QVariant")
    def playbackSongs(self):
        return self.database.songs()

    def _on_song(self, song: dict):
        self.database.upsert_song(song)
        self.database.commit()
        row = self.database.song_by_path(song["path"])
        if row:
            self.model.replaceByPath(dict(row))
            self.countChanged.emit()

    def _index_one(self, raw_path: str, only_if_changed: bool = False):
        path = Path(raw_path)
        if not path.exists() or not is_audio(path):
            return
        try:
            stat = path.stat()
            resolved = str(path.resolve())
            existing = self.database.song_by_path(resolved)
            if only_if_changed and existing:
                if (
                    existing["file_size"] == stat.st_size
                    and existing["modified_time"] == stat.st_mtime
                ):
                    return
            song = extract(path, self.artwork_cache)
            if song:
                self._on_song(song)
        except OSError:
            pass

    def _on_deleted(self, path: str):
        resolved = str(Path(path).resolve())
        self.database.delete_song(resolved)
        self.database.commit()
        self.model.removeByPath(resolved)
        self.countChanged.emit()

    def __del__(self):
        try:
            self.watcher.stop()
            self.database.close()
        except Exception:
            pass
