from __future__ import annotations

import json
from pathlib import Path


def load_text_file(path: str | Path) -> str:
    """Read UTF-8 text content from a file path."""
    return Path(path).read_text(encoding="utf-8")


def write_json_file(path: str | Path, payload: dict[str, object]) -> None:
    """Write JSON content with indentation and UTF-8 encoding."""
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
