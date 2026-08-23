from __future__ import annotations

import re
from pathlib import Path

from src.config import Config, DEFAULT_CONFIG
from src.llm.client import LocalLLMClient
from src.llm.mapper import SemanticQuestionMapper
from src.models import AnswerBlock, Candidate, ProcessingResult, Question
from src.preprocess import normalize_text
from src.validation import candidate_is_safe, validate_llm_result

_STRONG = re.compile(r"(?i)(?<![A-Za-z0-9])(?P<marker>(?:Q\s*\.?\s*\d+|Question\s*(?:No\.?\s*)?\d+))\s*(?P<tail>[.) :\-→]?)(?=\s|$)")
_WEAK = re.compile(r"^\s*(?P<marker>(?:\d+\s*[.)\]:]|\(\s*\d+\s*\)|\d+\s*→|[①②③④⑤⑥⑦⑧⑨]))\s*")
_PAGE = re.compile(r"(?i)^\s*(?:page\s+\d+|fig(?:ure)?\s+\d+(?:\.\d+)?|table\s+\d+(?:\.\d+)?|chapter\s+\d+|continued(?:\s+on\s+next\s+page)?)\s*[.!:]?\s*$")


def detect_candidates(text: str) -> list[Candidate]:
    candidates: list[Candidate] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        strong_matches = list(_STRONG.finditer(content))
        if strong_matches:
            for match in strong_matches:
                marker = match.group("marker")
                number_match = re.search(r"\d+", marker)
                candidates.append(Candidate(marker, int(number_match.group()) if number_match else None, offset + match.start(), offset + match.end(), "strong", content))
        else:
            weak = _WEAK.match(content)
            if weak:
                marker = weak.group("marker")
                number_match = re.search(r"\d+", marker)
                candidates.append(Candidate(marker, int(number_match.group()) if number_match else None, offset + weak.start(), offset + weak.end(), "weak", content))
        offset += len(line)
    return candidates


def _question_from_marker(marker: str, questions: dict[str, Question]) -> str | None:
    found = re.search(r"\d+", marker)
    if not found:
        return None
    question_id = f"Q{int(found.group())}"
    return question_id if not questions or question_id in questions else None


class AnswerProcessor:
    def __init__(self, config: Config = DEFAULT_CONFIG, llm: LocalLLMClient | None = None) -> None:
        self.config = config
        self.llm = llm or LocalLLMClient(config)
        self.mapper = SemanticQuestionMapper(self.llm)

    def process(self, student: str, raw_text: str, questions: dict[str, Question] | None = None, question_paper: str | None = None) -> ProcessingResult:
        questions = questions or {}
        normalized = normalize_text(raw_text)
        known_ids = set(questions)
        candidates = detect_candidates(normalized)
        accepted: list[Candidate] = []
        reviews: list[dict[str, object]] = []
        current: str | None = None
        llm_calls = 0
        for index, candidate in enumerate(candidates):
            question_id = _question_from_marker(candidate.marker, questions)
            safe = candidate_is_safe(candidate, known_ids, current) if questions else candidate.strength == "strong"
            if safe:
                accepted.append(candidate)
                current = question_id
                continue
            if candidate.strength == "weak" and current is not None:
                continue
            if llm_calls < self.config.max_llm_calls_per_document:
                llm_calls += 1
                previous = normalized[max(0, candidate.start - self.config.max_llm_context // 2):candidate.start]
                following_end = candidates[index + 1].start if index + 1 < len(candidates) else min(len(normalized), candidate.end + self.config.max_llm_context // 2)
                result = self.llm.analyze_structure({"canonical_questions": {key: value.question_text for key, value in questions.items()}, "candidate": candidate.line_text, "preceding": previous, "following": normalized[candidate.end:following_end], "current_question": current})
                result = validate_llm_result(result, known_ids)
                if result.decision == "question_boundary" and result.question_id and result.confidence >= self.config.question_confidence_threshold and not result.requires_human_review:
                    accepted.append(candidate)
                    current = result.question_id
                    continue
                reviews.append({"type": "ambiguous_boundary", "raw_text": candidate.line_text, "confidence": result.confidence, "possible_question_ids": [question_id] if question_id else [], "reason": result.reason})
                if candidate.strength == "strong":
                    accepted.append(candidate)
            else:
                reviews.append({"type": "ambiguous_boundary", "raw_text": candidate.line_text, "confidence": 0.0, "possible_question_ids": [], "reason": "LLM call budget exceeded."})
                if candidate.strength == "strong":
                    accepted.append(candidate)

        blocks: list[AnswerBlock] = []
        boundaries = accepted
        for index, candidate in enumerate(boundaries):
            end = boundaries[index + 1].start if index + 1 < len(boundaries) else len(normalized)
            answer_start = candidate.end
            answer = normalized[answer_start:end].strip()
            if not answer:
                continue
            question_id = _question_from_marker(candidate.marker, questions)
            is_resolved = question_id is not None
            blocks.append(AnswerBlock(answer, answer_start, end, candidate.marker, question_id, 0.98 if is_resolved and candidate.strength == "strong" else 0.0 if not is_resolved else 0.75, "confirmed" if is_resolved and candidate.strength == "strong" else "needs_human_review", index + 1))
        if self.config.llm_enabled and questions:
            for block in blocks:
                if block.resolved_question_id is None and llm_calls < self.config.max_llm_calls_per_document:
                    llm_calls += 1
                    mapped = self.mapper.map_block(block.text, questions, block.detected_marker)
                    if mapped.question_id and mapped.confidence >= self.config.question_confidence_threshold and not mapped.requires_human_review:
                        block.resolved_question_id = mapped.question_id
                        block.confidence = mapped.confidence
                        block.status = "confirmed"
                    else:
                        reviews.append({"type": "unmapped_answer", "raw_text": block.text, "confidence": mapped.confidence, "possible_question_ids": [], "reason": mapped.reason})
        if self.config.llm_enabled and not blocks and normalized.strip() and questions and llm_calls < self.config.max_llm_calls_per_document:
            llm_calls += 1
            mapped = self.mapper.map_block(normalized, questions)
            if mapped.question_id and mapped.confidence >= self.config.question_confidence_threshold and not mapped.requires_human_review:
                blocks.append(AnswerBlock(normalized, 0, len(normalized), None, mapped.question_id, mapped.confidence, "confirmed", 1))
        covered = [False] * len(normalized)
        for block in blocks:
            for position in range(block.source_start, min(block.source_end, len(covered))):
                covered[position] = True
        unmapped: list[dict[str, object]] = []
        if not blocks and normalized.strip():
            unmapped.append({"text": normalized, "source_start": 0, "source_end": len(normalized)})
            reviews.append({"type": "unmapped_answer", "raw_text": normalized, "confidence": 0.0, "possible_question_ids": [], "reason": "No validated question boundary was found."})
        result_questions: dict[str, dict[str, object]] = {}
        for question_id, question in questions.items():
            matching = [block for block in blocks if block.resolved_question_id == question_id]
            if len(matching) > 1:
                reviews.append({"type": "duplicate_question", "raw_text": " ".join(block.text for block in matching), "confidence": min(block.confidence for block in matching), "possible_question_ids": [question_id], "reason": "Multiple source blocks use the same question ID."})
            answer = matching[0] if matching else None
            result_questions[question_id] = {"number": question.number, "question": question.question_text, "question_text": question.question_text, "maximum_marks": question.max_marks, "max_marks": question.max_marks, "model_answer": question.model_answer, "student_answer": self._answer_payload(answer) if answer else None}
        if not questions:
            for block in blocks:
                result_questions.setdefault(block.resolved_question_id or "UNKNOWN", {"student_answer": self._answer_payload(block)})
        if questions:
            for block in blocks:
                if block.resolved_question_id not in questions:
                    unmapped.append(self._answer_payload(block))
        if boundaries and boundaries[0].start > 0:
            prefix = normalized[:boundaries[0].start].strip()
            if prefix and not _PAGE.match(prefix):
                reviews.append({"type": "unmapped_answer", "raw_text": prefix, "confidence": 0.0, "possible_question_ids": [], "reason": "Content precedes the first validated boundary."})
        return ProcessingResult(student, question_paper, result_questions, unmapped, "success", raw_text, normalized, reviews)

    @staticmethod
    def _answer_payload(block: AnswerBlock) -> dict[str, object]:
        return {"text": block.text, "confidence": block.confidence, "status": block.status, "source_order": block.source_order, "detected_marker": block.detected_marker, "resolved_question_id": block.resolved_question_id, "source_start": block.source_start, "source_end": block.source_end}
