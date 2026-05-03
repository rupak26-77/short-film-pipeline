import os
import re
from pathlib import Path
from typing import Tuple


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def validate_prompt(prompt: str) -> str:
    p = (prompt or "").strip()
    if not (10 <= len(p) <= 500):
        raise ValueError("prompt length must be 10–500 characters")
    return p


def validate_asset_exists(assets_audio_dir: Path, audio_file: str) -> Path:
    if not audio_file:
        raise ValueError("audio_file is required")
    ensure_safe_filename(audio_file)
    audio_path = (assets_audio_dir / audio_file).resolve()
    ensure_within_dir(audio_path, assets_audio_dir.resolve())
    if not audio_path.exists():
        raise FileNotFoundError(f"audio file not found in assets/audio/: {audio_file}")
    return audio_path


def ensure_safe_filename(name: str) -> None:
    # Allow spaces and common characters, but forbid any path traversal/separators.
    # This is important because users often have assets like "song 01.mp3".
    if not name or len(name) > 255:
        raise ValueError("unsafe filename")
    if any(sep in name for sep in ["/", "\\"]):
        raise ValueError("unsafe filename")
    if "\x00" in name or name.strip() != name:
        raise ValueError("unsafe filename")
    if name in {".", ".."} or ".." in name:
        raise ValueError("unsafe filename")


def ensure_within_dir(path: Path, parent_dir: Path) -> None:
    parent_dir = parent_dir.resolve()
    path = path.resolve()
    if parent_dir not in path.parents and path != parent_dir:
        raise ValueError("path escapes allowed directory")


def format_mmss(seconds: float) -> str:
    s = max(0.0, float(seconds))
    m = int(s // 60)
    r = int(round(s - 60 * m))
    return f"{m:02d}:{r:02d}"


def audio_info_from_pydub_channels_samplewidth(channels: int, sample_width_bytes: int) -> Tuple[int, int]:
    bit_depth = int(sample_width_bytes) * 8
    return channels, bit_depth
