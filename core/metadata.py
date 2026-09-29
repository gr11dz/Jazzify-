from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from mutagen import File

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus",
    ".wma", ".aiff", ".aif", ".ape", ".wv",
}


def is_audio(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def _first(tags: Any, *keys: str, default: str = "") -> str:
    if not tags:
        return default
    for key in keys:
        value = tags.get(key)
        if value:
            if isinstance(value, (list, tuple)):
                value = value[0]
            return str(value)
    return default


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = [max(0, min(255, int(x))) for x in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def extract_palette(image: Any) -> tuple[str, str, str]:
    """Return primary, secondary and dark background colors from artwork."""
    try:
        from PIL import ImageStat

        small = image.convert("RGB")
        small.thumbnail((48, 48))
        # Quantization is cheap at this size and gives visually useful clusters.
        quantized = small.quantize(colors=6, method=2).convert("RGB")
        palette = quantized.getcolors(maxcolors=48 * 48) or []
        palette.sort(key=lambda item: item[0], reverse=True)

        colors = [color for _, color in palette[:6]]
        if not colors:
            mean = ImageStat.Stat(small).mean
            base = tuple(int(v) for v in mean)
            dark = tuple(int(v * 0.30) for v in base)
            return _rgb_hex(base), _rgb_hex(base), _rgb_hex(dark)

        primary = colors[0]
        secondary = colors[1] if len(colors) > 1 else primary

        # Blend the darkest cluster into a subdued UI background.
        darkest = sorted(
            colors,
            key=lambda c: (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]),
        )[0]
        background = tuple(int(channel * 0.28) for channel in darkest)

        return (
            _rgb_hex(primary),
            _rgb_hex(secondary),
            _rgb_hex(background),
        )
    except Exception:
        return "#9B8CFF", "#5F6FFF", "#090A0F"


def _extract_artwork(audio: Any, artwork_cache: Path) -> tuple[str, str, str, str]:
    picture_data = None
    tags = getattr(audio, "tags", None)

    if tags:
        try:
            try:
                apics = tags.getall("APIC")
            except Exception:
                apics = []

            if apics:
                picture_data = apics[0].data

            if picture_data is None:
                for tag in tags.values():
                    if tag.__class__.__name__ == "APIC":
                        picture_data = tag.data
                        break
        except Exception:
            pass

    if picture_data is None:
        pictures = getattr(audio, "pictures", None)
        if pictures:
            try:
                pics = list(pictures)
                if pics:
                    picture_data = pics[0].data
            except Exception:
                pass

    if not picture_data:
        return "", "", "", ""

    digest = hashlib.sha1(picture_data).hexdigest()
    artwork_cache.mkdir(parents=True, exist_ok=True)
    cached = artwork_cache / f"{digest}.jpg"

    try:
        from PIL import Image

        image = Image.open(io.BytesIO(picture_data)).convert("RGB")
        palette = extract_palette(image)

        if not cached.exists():
            image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            image.save(cached, "JPEG", quality=90, optimize=True)

        return str(cached), *palette

    except Exception:
        try:
            if not cached.exists():
                cached.write_bytes(picture_data)
            return str(cached), "#9B8CFF", "#5F6FFF", "#090A0F"
        except OSError:
            return "", "", "", ""


def extract(path: Path, artwork_cache: Path) -> dict[str, Any] | None:
    try:
        stat = path.stat()
        audio = File(path, easy=False)
        if audio is None:
            return None

        tags = audio.tags or {}
        info = getattr(audio, "info", None)

        title = _first(tags, "TIT2", "©nam", "title", default=path.stem)
        artist = _first(tags, "TPE1", "©ART", "artist")
        album = _first(tags, "TALB", "©alb", "album")
        album_artist = _first(tags, "TPE2", "aART", "albumartist")
        genre = _first(tags, "TCON", "©gen", "genre")
        year_text = _first(tags, "TDRC", "©day", "date")
        track_text = _first(tags, "TRCK", "trkn", "tracknumber")

        try:
            year = int(str(year_text)[:4]) if year_text else None
        except ValueError:
            year = None

        try:
            track_number = int(str(track_text).split("/")[0]) if track_text else None
        except ValueError:
            track_number = None

        artwork_path, primary, secondary, background = _extract_artwork(
            audio,
            artwork_cache,
        )

        return {
            "path": str(path.resolve()),
            "title": title,
            "artist": artist,
            "album": album,
            "album_artist": album_artist,
            "genre": genre,
            "year": year,
            "track_number": track_number,
            "duration": float(info.length) if info and info.length else 0.0,
            "file_size": stat.st_size,
            "modified_time": stat.st_mtime,
            "artwork_path": artwork_path,
            "primary_color": primary,
            "secondary_color": secondary,
            "background_color": background,
        }
    except (OSError, ValueError, TypeError):
        return None
