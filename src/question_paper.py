from __future__ import annotations

import re
from pathlib import Path

from src.models import Question

_MARKER = re.compile(r"(?im)(?<![A-Za-z0-9])(?:Q\s*\.?\s*(?P<qnum>\d+)|Question\s*(?:No\.?\s*)?(?P<question_num>\d+)|(?P<plain>\d+)\s*[.):])\s*[.) :\-]?")
_MARKS = re.compile(r"(?ix)(?:\[\s*(\d+)\s*(?:marks?)?\s*\]|\(\s*(\d+)\s*(?:marks?)?\s*\)|\b(?:max\s+)?marks?\s*[:\-]?\s*(\d+)|\b(\d+)\s*M\b)")
_HEADING = re.compile(r"(?im)^\s*#+\s*(?P<marker>Q\s*\.?\s*\d+|Question\s*(?:No\.?\s*)?\d+)\s*[.) :\-]?\s*(?P<body>.*)$")


def _number(match: re.Match[str]) -> int:
    return int(next(value for value in match.groups() if value is not None))


def parse_question_paper(text: str) -> dict[str, Question]:
    headings = list(_HEADING.finditer(text or ""))
    if headings:
        questions: dict[str, Question] = {}
        for heading in headings:
            number_match = re.search(r"\d+", heading.group("marker"))
            if not number_match:
                continue
            body = heading.group("body").strip()
            mark_matches = list(_MARKS.finditer(body))
            max_marks = None
            if mark_matches:
                mark = mark_matches[-1]
                max_marks = int(next(value for value in mark.groups() if value is not None))
                body = (body[:mark.start()] + body[mark.end():]).strip()
            if body:
                number = int(number_match.group())
                question_id = f"Q{number}"
                questions[question_id] = Question(question_id, number, body, max_marks)
        if questions:
            return questions
    matches = list(_MARKER.finditer(text or ""))
    questions: dict[str, Question] = {}
    for index, match in enumerate(matches):
        number = _number(match)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        mark_matches = list(_MARKS.finditer(body))
        max_marks = None
        if mark_matches:
            mark = mark_matches[-1]
            max_marks = int(next(value for value in mark.groups() if value is not None))
            body = (body[:mark.start()] + body[mark.end():]).strip()
        if not body or re.match(r"(?i)^(answer all|attempt any|section\s|total marks|time\s|page\s|continued)", body):
            continue
        question_id = f"Q{number}"
        questions[question_id] = Question(question_id, number, re.sub(r"\s+", " ", body), max_marks)
    return questions


def load_question_paper(path: str | Path | None) -> dict[str, Question]:
    if not path or not Path(path).exists():
        return {}
    return parse_question_paper(Path(path).read_text(encoding="utf-8"))
