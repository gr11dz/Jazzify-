from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .metadata import is_audio


class _Handler(FileSystemEventHandler):
    def __init__(self, owner: "Watcher"):
        super().__init__()
        self.owner = owner

    def on_created(self, event):
        if not event.is_directory and is_audio(Path(event.src_path)):
            self.owner.created.emit(str(Path(event.src_path).resolve()))

    def on_modified(self, event):
        if not event.is_directory and is_audio(Path(event.src_path)):
            self.owner.modified.emit(str(Path(event.src_path).resolve()))

    def on_deleted(self, event):
        if not event.is_directory and is_audio(Path(event.src_path)):
            self.owner.deleted.emit(str(Path(event.src_path).resolve()))


class Watcher(QObject):
    created = Signal(str)
    modified = Signal(str)
    deleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.observer: Observer | None = None

    def start(self, folders: list[str]) -> None:
        self.stop()
        observer = Observer()
        handler = _Handler(self)
        for folder in folders:
            path = Path(folder)
            if path.is_dir():
                observer.schedule(handler, str(path), recursive=True)
        observer.start()
        self.observer = observer

    def stop(self) -> None:
        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2)
            self.observer = None
