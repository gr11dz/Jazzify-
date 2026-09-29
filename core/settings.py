from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot


class Settings(QObject):
    waveformAlwaysOnChanged = Signal(bool)

    def __init__(self, path: Path):
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {
            "music_folders": [],
            "waveform_always_on": False,
        }
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._save()
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._data.update(loaded)
        except (OSError, json.JSONDecodeError):
            self._save()

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @property
    def music_folders(self) -> list[str]:
        return list(self._data.get("music_folders", []))

    def set_music_folders(self, folders: list[str]) -> None:
        self._data["music_folders"] = list(folders)
        self._save()

    @Property(bool, notify=waveformAlwaysOnChanged)
    def waveformAlwaysOn(self) -> bool:
        return bool(self._data.get("waveform_always_on", False))

    @Slot(bool)
    def setWaveformAlwaysOn(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self.waveformAlwaysOn:
            return
        self._data["waveform_always_on"] = enabled
        self._save()
        self.waveformAlwaysOnChanged.emit(enabled)
