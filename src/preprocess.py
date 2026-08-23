from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalize OCR output before segmentation without relying on line breaks."""
    if text is None:
        return ""

    normalized = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    normalized = normalized.replace("\t", " ")
    normalized = re.sub(r"\u00a0+", " ", normalized)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    normalized = re.sub(r"(?:<\|im_[^>\n]*>|<\|im_end\|>)", "", normalized)
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = normalized.strip()
    return normalized


def split_logical_lines(text: str) -> list[str]:
    """Split into logical lines while preserving reading order."""
    if not text:
        return []

    lines = [line.strip() for line in text.split("\n")]
    return [line for line in lines if line]
