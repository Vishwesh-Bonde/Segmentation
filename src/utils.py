from __future__ import annotations

from pathlib import Path


def iter_text_files(input_dir: str | Path) -> list[Path]:
    """Return text files in sorted order, skipping hidden and empty files."""
    directory = Path(input_dir)
    if not directory.exists():
        return []

    files: list[Path] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() != ".txt":
            continue
        files.append(path)
    return files
