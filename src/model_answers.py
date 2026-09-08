from __future__ import annotations

import re
from pathlib import Path

from src.models import Question

_HEADING = re.compile(
    r"(?im)^\s*#+\s*(?P<marker>Q\s*\.?\s*(?P<number>\d+))\s*(?:[.):\-]|\s)\s*(?P<body>.*?)(?:\s*\[(?P<marks>\d+)\s*(?:marks?)?\]\s*)?$"
)


def parse_model_answers(path: str | Path | None) -> dict[str, Question]:
    if not path or not Path(path).exists():
        return {}

    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    questions: dict[str, Question] = {}

    for index, line in enumerate(lines):
        match = _HEADING.match(line)
        if not match:
            continue

        question_id = f"Q{int(match.group('number'))}"
        question_text = (match.group('body') or '').strip()
        max_marks = None
        if match.group('marks'):
            max_marks = int(match.group('marks'))

        answer_parts: list[str] = []
        for next_line in lines[index + 1:]:
            if re.match(r"^\s*#+\s*Q\s*\.?\s*\d+", next_line, flags=re.IGNORECASE):
                break
            answer_parts.append(next_line.rstrip())

        model_answer = "\n".join(part.rstrip() for part in answer_parts).strip()
        if not question_text and not model_answer:
            continue

        questions[question_id] = Question(
            question_id=question_id,
            number=int(match.group('number')),
            question_text=question_text,
            max_marks=max_marks,
            model_answer=model_answer,
        )

    return questions


def load_model_answers(path: str | Path | None) -> dict[str, str]:
    questions = parse_model_answers(path)
    return {question_id: question.model_answer or "" for question_id, question in questions.items()}
