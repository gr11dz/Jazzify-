from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from .metadata import extract, is_audio


class JobSignals(QObject):
    finished = Signal()


class IndexJob(QRunnable):
    def __init__(self, root: Path, callback, artwork_cache: Path):
        super().__init__()
        self.root = root
        self.callback = callback
        self.artwork_cache = artwork_cache
        self.signals = JobSignals()

    def run(self) -> None:
        try:
            for path in self.root.rglob("*"):
                if path.is_file() and is_audio(path):
                    song = extract(path, self.artwork_cache)
                    if song:
                        self.callback(song)
        except OSError:
            pass
        finally:
            self.signals.finished.emit()


class Indexer(QObject):
    songFound = Signal(dict)
    indexStarted = Signal()
    indexFinished = Signal()

    def __init__(self, artwork_cache: Path):
        super().__init__()
        self.artwork_cache = artwork_cache
        self.pool = QThreadPool.globalInstance()
        self._active_jobs = 0

    def index(self, root: str) -> None:
        path = Path(root)
        if not path.is_dir():
            return

        job = IndexJob(path, self._song_found, self.artwork_cache)
        self._active_jobs += 1
        self.indexStarted.emit()
        job.signals.finished.connect(self._job_finished)
        self.pool.start(job)

    @Slot()
    def _job_finished(self) -> None:
        self._active_jobs = max(0, self._active_jobs - 1)
        if self._active_jobs == 0:
            self.indexFinished.emit()

    @Slot(dict)
    def _song_found(self, song: dict) -> None:
        self.songFound.emit(song)
