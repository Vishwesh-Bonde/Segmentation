from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict

import re

from src.preprocess import normalize_text
from src.regex_patterns import extract_question_number, iter_question_matches, strip_question_prompt


class QuestionDetector(ABC):
    """Abstract interface for question detection strategies."""

    @abstractmethod
    def detect(self, line: str) -> tuple[str | None, str]:
        """Return normalized question label and remaining text."""


class RegexQuestionDetector(QuestionDetector):
    """Concrete regex-based detector for OCR question markers."""

    def detect(self, line: str) -> tuple[str | None, str]:
        return extract_question_number(line)


class QuestionSegmenter:
    """Segments OCR text into question/answer mappings."""

    def __init__(self, detector: QuestionDetector | None = None) -> None:
        self.detector = detector or RegexQuestionDetector()

    def segment_text(self, text: str) -> dict[str, str]:
        if text is None:
            return {"UNKNOWN": "Entire OCR Text"}

        normalized = normalize_text(text)
        if not normalized:
            return {"UNKNOWN": "Entire OCR Text"}

        matches = list(iter_question_matches(normalized))
        if not matches:
            return {"UNKNOWN": normalized}

        answers: OrderedDict[str, str] = OrderedDict()

        for index, (match, question_id) in enumerate(matches):
            start = match.start()
            end = matches[index + 1][0].start() if index + 1 < len(matches) else len(normalized)
            answer_text = normalized[match.end():end]
            answer = self._clean_answer(answer_text)

            if answer:
                self._store_answer(answers, question_id, answer)

        if not answers:
            return {"UNKNOWN": normalized}

        return dict(answers)

    def _clean_answer(self, answer_text: str) -> str:
        cleaned = (answer_text or "").strip()
        if not cleaned:
            return ""
        if re.match(r"^(?:In\s+your\s+own\s+words,\s*)?(?:Explain|Describe|Define|State|List|What\s+is|What\s+are|Why|How|When|Where|Who|Which)\b", cleaned, re.IGNORECASE):
            cleaned = strip_question_prompt(cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _merge_answer(self, lines: list[str]) -> str:
        return " ".join(part.strip() for part in lines if part and part.strip()).strip()

    def _store_answer(self, answers: OrderedDict[str, str], question: str, value: str) -> None:
        normalized_key = self._normalize_question_key(question)
        if normalized_key in answers:
            answers[normalized_key] = f"{answers[normalized_key]} {value}".strip()
        else:
            answers[normalized_key] = value

    def _normalize_question_key(self, question: str) -> str:
        if not question:
            return "UNKNOWN"
        q_value = question.strip().upper()
        if q_value.startswith("Q") and q_value[1:].isdigit():
            return f"Q{q_value[1:]}"
        if q_value.isdigit():
            return f"Q{q_value}"
        return q_value
