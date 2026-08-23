from __future__ import annotations

import re
from pathlib import Path


_HEADING = re.compile(r"(?im)^\s*#+\s*(Q\s*\.?\s*\d+)\s*[.) :\-]?\s*.*$")


def load_model_answers(path: str | Path | None) -> dict[str, str]:
    if not path or not Path(path).exists():
        return {}
    text = Path(path).read_text(encoding="utf-8")
    headings = list(_HEADING.finditer(text))
    answers: dict[str, str] = {}
    for index, heading in enumerate(headings):
        number = re.search(r"\d+", heading.group(1))
        if not number:
            continue
        question_id = f"Q{int(number.group())}"
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        answer = text[heading.end():end].strip()
        if answer:
            answers[question_id] = answer
    return answers