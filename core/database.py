from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    added_at REAL NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    artist TEXT NOT NULL DEFAULT '',
    album TEXT NOT NULL DEFAULT '',
    album_artist TEXT NOT NULL DEFAULT '',
    genre TEXT NOT NULL DEFAULT '',
    year INTEGER,
    track_number INTEGER,
    duration REAL NOT NULL DEFAULT 0,
    file_size INTEGER NOT NULL DEFAULT 0,
    modified_time REAL NOT NULL DEFAULT 0,
    artwork_path TEXT NOT NULL DEFAULT '',
    primary_color TEXT NOT NULL DEFAULT '',
    secondary_color TEXT NOT NULL DEFAULT '',
    background_color TEXT NOT NULL DEFAULT '',
    added_at REAL NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist);
CREATE INDEX IF NOT EXISTS idx_songs_album ON songs(album);
CREATE INDEX IF NOT EXISTS idx_songs_path ON songs(path);
CREATE INDEX IF NOT EXISTS idx_songs_modified ON songs(modified_time);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        existing = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(songs)")
        }

        additions = {
            "primary_color": "TEXT NOT NULL DEFAULT ''",
            "secondary_color": "TEXT NOT NULL DEFAULT ''",
            "background_color": "TEXT NOT NULL DEFAULT ''",
        }

        for column, definition in additions.items():
            if column not in existing:
                self.conn.execute(
                    f"ALTER TABLE songs ADD COLUMN {column} {definition}"
                )

    def close(self) -> None:
        try:
            self.conn.commit()
            self.conn.close()
        except sqlite3.Error:
            pass

    def add_folder(self, path: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO folders(path) VALUES (?)",
            (path,),
        )
        self.conn.commit()

    def remove_folder(self, path: str) -> None:
        path = str(Path(path).resolve())
        self.conn.execute("DELETE FROM folders WHERE path = ?", (path,))
        self.conn.execute(
            "DELETE FROM songs WHERE path = ? OR path LIKE ?",
            (path, path.rstrip("\\/") + "\\%"),
        )
        self.conn.commit()

    def folders(self) -> list[str]:
        return [
            row[0]
            for row in self.conn.execute(
                "SELECT path FROM folders ORDER BY path"
            )
        ]

    def song_by_path(self, path: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM songs WHERE path = ?",
            (path,),
        ).fetchone()

    def upsert_song(self, song: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO songs
            (path,title,artist,album,album_artist,genre,year,track_number,
             duration,file_size,modified_time,artwork_path,primary_color,
             secondary_color,background_color)
            VALUES
            (:path,:title,:artist,:album,:album_artist,:genre,:year,:track_number,
             :duration,:file_size,:modified_time,:artwork_path,:primary_color,
             :secondary_color,:background_color)
            ON CONFLICT(path) DO UPDATE SET
                title=excluded.title,
                artist=excluded.artist,
                album=excluded.album,
                album_artist=excluded.album_artist,
                genre=excluded.genre,
                year=excluded.year,
                track_number=excluded.track_number,
                duration=excluded.duration,
                file_size=excluded.file_size,
                modified_time=excluded.modified_time,
                artwork_path=excluded.artwork_path,
                primary_color=excluded.primary_color,
                secondary_color=excluded.secondary_color,
                background_color=excluded.background_color
            """,
            song,
        )

    def update_visuals(
        self,
        path: str,
        primary_color: str,
        secondary_color: str,
        background_color: str,
    ) -> None:
        self.conn.execute(
            """
            UPDATE songs
            SET primary_color = ?, secondary_color = ?, background_color = ?
            WHERE path = ?
            """,
            (primary_color, secondary_color, background_color, path),
        )

    def delete_song(self, path: str) -> None:
        self.conn.execute("DELETE FROM songs WHERE path = ?", (path,))

    def commit(self) -> None:
        self.conn.commit()

    def songs(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM songs ORDER BY added_at DESC, title COLLATE NOCASE, artist COLLATE NOCASE"
        )
        return [dict(row) for row in rows]
