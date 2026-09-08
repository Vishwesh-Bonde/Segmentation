from __future__ import annotations

import re
<<<<<<< HEAD
=======
from pathlib import Path

>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
from src.config import Config, DEFAULT_CONFIG
from src.llm.client import LocalLLMClient
from src.llm.mapper import SemanticQuestionMapper
from src.models import AnswerBlock, Candidate, ProcessingResult, Question
from src.preprocess import normalize_text
<<<<<<< HEAD
from src.validation import validate_llm_result

_STRONG = re.compile(r"(?i)(?<![A-Za-z0-9])(?P<marker>(?:Q\s*\.?\s*\d+|Question\s*(?:No\.?\s*)?\d+))\s*(?P<tail>[.) :\-→]?)(?=\s|$)")
_WEAK = re.compile(r"^\s*(?P<marker>(?:\d+\s*\.\)|\d+\s*[):\]]|\d+\s*\.|\(\s*\d+\s*\)|\d+\s*→|[①②③④⑤⑥⑦⑧⑨]))\s*")
_PAGE = re.compile(r"(?i)^\s*(?:page\s+\d+|fig(?:ure)?\s+\d+(?:\.\d+)?|table\s+\d+(?:\.\d+)?|chapter\s+\d+|continued(?:\s+on\s+next\s+page)?)\s*[.!:]?\s*$")
_LEADING_BLOCK_MIN_CHARS = 120
=======
from src.validation import candidate_is_safe, validate_llm_result

_STRONG = re.compile(r"(?i)(?<![A-Za-z0-9])(?P<marker>(?:Q\s*\.?\s*\d+|Question\s*(?:No\.?\s*)?\d+))\s*(?P<tail>[.) :\-→]?)(?=\s|$)")
_WEAK = re.compile(r"^\s*(?P<marker>(?:\d+\s*[.)\]:]|\(\s*\d+\s*\)|\d+\s*→|[①②③④⑤⑥⑦⑧⑨]))\s*")
_PAGE = re.compile(r"(?i)^\s*(?:page\s+\d+|fig(?:ure)?\s+\d+(?:\.\d+)?|table\s+\d+(?:\.\d+)?|chapter\s+\d+|continued(?:\s+on\s+next\s+page)?)\s*[.!:]?\s*$")
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5


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


<<<<<<< HEAD
def _canonical_context(questions: dict[str, Question]) -> dict[str, dict[str, str]]:
    return {
        key: {
            "question": value.question_text,
            "model_answer_excerpt": (value.model_answer or "")[:150],
        }
        for key, value in questions.items()
    }


def _ordered_questions(questions: dict[str, Question]) -> list[Question]:
    return sorted(questions.values(), key=lambda question: question.number)


def _preamble_is_header(preamble: str) -> bool:
    """True when the text before the first candidate looks like a paper title/header
    rather than the start of an actual answer."""
    if not preamble:
        return True
    if _PAGE.match(preamble.strip()):
        return True
    lines = [line for line in preamble.strip().splitlines() if line.strip()]
    if len(lines) == 1 and len(preamble.strip()) <= 80:
        return True
    return False


class _BoundaryClassifier:
    """Deterministic structural classification of weak OCR markers against the
    canonical question set. The LLM is only consulted for genuinely ambiguous
    candidates where marker numbers disagree with the document's question order."""

    def __init__(self, questions: dict[str, Question], implicit_first: bool = False) -> None:
        self.ordered = _ordered_questions(questions)
        self.positions: dict[int, int] = {
            question.number: index for index, question in enumerate(self.ordered)
        }
        self.n = len(self.ordered)
        self._opened: set[int] = set()
        self._implicit: int | None = 0 if implicit_first else None

    def mark_opened(self, question_id: str | None) -> None:
        if question_id is None:
            return
        found = re.search(r"\d+", question_id)
        if not found:
            return
        number = int(found.group())
        if number in self.positions:
            self._opened.add(self.positions[number])

    @property
    def opened(self) -> set[int]:
        return set(self._opened)

    def _effective(self) -> set[int]:
        opened = set(self._opened)
        if self._implicit is not None:
            opened.add(self._implicit)
        return opened

    def _next_fill(self) -> int:
        effective = self._effective()
        for index in range(self.n):
            if index not in effective:
                return index
        return self.n

    def classify(self, candidate: Candidate, preamble_meaningful: bool, suppressed: bool = False) -> str:
        """Return one of 'boundary', 'continuation', 'ambiguous'."""
        if candidate.number is None or candidate.number not in self.positions:
            return "continuation"
        index = self.positions[candidate.number]
        if not self._opened and preamble_meaningful:
            return "continuation"
        next_fill = self._next_fill()
        if index < next_fill:
            return "continuation"
        if index == next_fill:
            if self._effective() == set(range(next_fill)):
                return "continuation" if suppressed else "boundary"
            return "ambiguous"
        return "ambiguous"


def _suppressed(candidates: list[Candidate], index: int) -> bool:
    """A weak marker is suppressed when the same number repeats later in the
    document (numbered sub-points inside an answer repeat numbers; question
    markers do not), unless the marker is an arrow-style dedicated question
    marker."""
    candidate = candidates[index]
    if "→" in candidate.marker:
        return False
    number = candidate.number
    if number is None:
        return False
    for other in candidates[index + 1:]:
        if other.number == number:
            return True
    return False


def _is_numbered_run(candidates: list[Candidate], index: int) -> bool:
    """True when the marker is a weak numbered item whose immediate successor is
    another weak marker numbered +1. Such consecutive runs (1., 2., 3., ...) are
    internal numbered lists climbing through the canonical ordinals; a real
    question marker is never immediately followed by its sibling +1 marker."""
    candidate = candidates[index]
    if "→" in candidate.marker:
        return False
    if candidate.number is None or index + 1 >= len(candidates):
        return False
    successor = candidates[index + 1]
    return successor.strength == "weak" and successor.number == candidate.number + 1


def _is_prefix_block(block: AnswerBlock, blocks: list[AnswerBlock], questions: dict[str, Question]) -> bool:
    return bool(
        questions
        and "Q1" in questions
        and block.detected_marker is None
        and block.source_order == 1
        and block.source_start == 0
        and len(blocks) > 1
        and len(block.text.strip()) >= _LEADING_BLOCK_MIN_CHARS
    )


=======
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
class AnswerProcessor:
    def __init__(self, config: Config = DEFAULT_CONFIG, llm: LocalLLMClient | None = None) -> None:
        self.config = config
        self.llm = llm or LocalLLMClient(config)
        self.mapper = SemanticQuestionMapper(self.llm)

<<<<<<< HEAD
    def _merge_adjacent_same_question(self, blocks: list[AnswerBlock], normalized: str) -> list[AnswerBlock]:
        merged: list[AnswerBlock] = []
        for block in blocks:
            marker_gap = (
                normalized[merged[-1].source_end:block.source_start].strip()
                if merged
                else ""
            )
            if (
                merged
                and merged[-1].resolved_question_id is not None
                and block.resolved_question_id == merged[-1].resolved_question_id
                and bool(marker_gap)
                and marker_gap == (block.detected_marker or "").strip()
                and not _STRONG.search(block.detected_marker or "")
            ):
                previous_block = merged[-1]
                previous_block.text = normalized[previous_block.source_start:block.source_end]
                previous_block.source_end = block.source_end
                previous_block.confidence = max(previous_block.confidence, block.confidence)
            else:
                merged.append(block)
        return merged

=======
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
    def process(self, student: str, raw_text: str, questions: dict[str, Question] | None = None, question_paper: str | None = None) -> ProcessingResult:
        questions = questions or {}
        normalized = normalize_text(raw_text)
        known_ids = set(questions)
        candidates = detect_candidates(normalized)
        accepted: list[Candidate] = []
<<<<<<< HEAD
        review_items: list[dict[str, object]] = []
        llm_calls = 0
        segmentation_llm_calls = 0
        mapping_llm_calls = 0

        preamble = (normalized[:candidates[0].start].strip() if candidates else "") if normalized else ""
        implicit_first = bool(preamble) and not _preamble_is_header(preamble)
        classifier = _BoundaryClassifier(questions, implicit_first=implicit_first) if questions else None

        for index, candidate in enumerate(candidates):
            if not questions:
                if candidate.strength == "strong":
                    accepted.append(candidate)
                continue

            explicit_question_id = _question_from_marker(candidate.marker, questions)
            if candidate.strength == "strong" and explicit_question_id is not None:
                accepted.append(candidate)
                classifier.mark_opened(explicit_question_id)
                continue

            if candidate.strength == "weak" and classifier is not None:
                current_preamble = normalized[:candidate.start].strip()
                ruling = classifier.classify(
                    candidate,
                    preamble_meaningful=bool(current_preamble) and not _preamble_is_header(current_preamble),
                    suppressed=_suppressed(candidates, index),
                )
                if ruling == "boundary":
                    accepted.append(candidate)
                    classifier.mark_opened(f"Q{candidate.number}")
                    continue
                if ruling == "continuation":
                    continue
                if ruling == "ambiguous" and _is_numbered_run(candidates, index):
                    continue

            if (
                llm_calls >= self.config.max_llm_calls_per_document
                or segmentation_llm_calls >= self.config.max_segmentation_llm_calls_per_document
            ):
                review_items.append({"text": candidate.line_text, "possible_questions": []})
                continue

            llm_calls += 1
            segmentation_llm_calls += 1
            following_end = candidates[index + 1].start if index + 1 < len(candidates) else min(len(normalized), candidate.end + self.config.max_llm_context // 2)
            context = {
                "operation": "boundary",
                "canonical_questions": _canonical_context(questions),
                "candidate": candidate.line_text,
                "candidate_marker": candidate.marker,
                "candidate_position": index + 1,
                "candidate_count": len(candidates),
                "all_candidate_markers": [item.marker for item in candidates],
                "preceding": normalized[max(0, candidate.start - self.config.max_llm_context // 2):candidate.start],
                "following": normalized[candidate.end:following_end],
            }
            if index > 0:
                context["previous_candidate"] = {
                    "marker": candidates[index - 1].marker,
                    "line": candidates[index - 1].line_text,
                }
            result = self.llm.analyze_structure(context)
            result = validate_llm_result(result, known_ids, operation="boundary")
            if (
                result.decision == "question_boundary"
                and result.question_id is not None
                and result.confidence >= self.config.question_confidence_threshold
                and not result.requires_human_review
            ):
                accepted.append(candidate)
                classifier.mark_opened(result.question_id)
            elif result.requires_human_review:
                possible = [result.question_id] if result.question_id else []
                review_items.append({"text": candidate.line_text, "possible_questions": possible})

        blocks: list[AnswerBlock] = []
        boundaries = accepted
        if normalized and boundaries and boundaries[0].start > 0:
            prefix = normalized[:boundaries[0].start].strip()
            if prefix and not _PAGE.match(prefix):
                blocks.append(AnswerBlock(prefix, 0, boundaries[0].start, None, None, 0.0, "needs_mapping", 1))
        elif normalized and not boundaries:
            blocks.append(AnswerBlock(normalized, 0, len(normalized), None, None, 0.0, "needs_mapping", 1))

=======
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
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
        for index, candidate in enumerate(boundaries):
            end = boundaries[index + 1].start if index + 1 < len(boundaries) else len(normalized)
            answer_start = candidate.end
            answer = normalized[answer_start:end].strip()
            if not answer:
                continue
<<<<<<< HEAD
            blocks.append(AnswerBlock(answer, answer_start, end, candidate.marker, None, 0.0, "needs_mapping", len(blocks) + 1))

        structless_document = bool(
            questions
            and len(candidates) > 1
            and len(blocks) == 1
            and blocks[0].detected_marker is None
        )

        if self.config.llm_enabled and questions:
            mapped_ids: list[str] = []
            for block in blocks:
                if llm_calls >= self.config.max_llm_calls_per_document:
                    review_items.append({"text": block.text, "possible_questions": list(questions)})
                    continue
                if structless_document:
                    block.status = "unmapped"
                    review_items.append({"text": block.text, "possible_questions": list(questions)})
                    continue
                llm_calls += 1
                mapping_llm_calls += 1
                surrounding_context = (
                    f"Earlier answer blocks mapped to: {mapped_ids}. "
                    f"Canonical questions not yet mapped: "
                    f"{[question_id for question_id in questions if question_id not in mapped_ids]}."
                )
                mapped = self.mapper.map_block(
                    block.text,
                    questions,
                    block.detected_marker,
                    surrounding_context=surrounding_context,
                )
                if _is_prefix_block(block, blocks, questions):
                    block.resolved_question_id = "Q1"
                    block.confidence = mapped.confidence if mapped.question_id == "Q1" else 0.6
                    block.status = "confirmed"
                    mapped_ids.append("Q1")
                elif (
                    mapped.decision == "mapped"
                    and mapped.question_id
                    and mapped.subject_match is True
                    and mapped.confidence >= self.config.question_confidence_threshold
                    and not mapped.requires_human_review
                ):
                    block.resolved_question_id = mapped.question_id
                    block.confidence = mapped.confidence
                    block.status = "confirmed"
                    mapped_ids.append(mapped.question_id)
                else:
                    block.status = "unmapped"
                    review_items.append({"text": block.text, "possible_questions": list(questions)})

        if not self.config.llm_enabled and blocks:
            review_items.extend({"text": block.text, "possible_questions": list(questions)} for block in blocks)

        blocks = self._merge_adjacent_same_question(blocks, normalized)

        suspicious_single_block = bool(
            questions
            and len(candidates) > 1
            and len(blocks) == 1
            and all(block.status == "unmapped" or block.resolved_question_id is None for block in blocks)
        )

        unmapped_items: list[str] = []
        if suspicious_single_block:
            review_items.append({
                "text": blocks[0].text,
                "possible_questions": list(questions),
            })
            blocks[0].status = "unmapped"
            blocks[0].resolved_question_id = None
        elif self.config.llm_enabled and not blocks and normalized.strip() and questions:
            unmapped_items.append(normalized)

        result_questions: dict[str, str | list[str] | None] = {question_id: None for question_id in questions}
        for question_id in questions:
            matching = [block for block in blocks if block.resolved_question_id == question_id]
            if len(matching) > 1:
                result_questions[question_id] = [block.text for block in matching]
            elif len(matching) == 1:
                result_questions[question_id] = matching[0].text

        for block in blocks:
            if block.status == "unmapped":
                unmapped_items.append(block.text)

        if not blocks and normalized.strip() and not self.config.llm_enabled:
            unmapped_items.append(normalized)
            review_items.append({"text": normalized, "possible_questions": list(questions)})

        unmapped_items = list(dict.fromkeys(unmapped_items))

        minimal_review = []
        seen: set[tuple[str, tuple[str, ...]]] = set()
        for item in review_items:
            text = str(item.get("text", "")).strip()
            possible = tuple(sorted(str(value) for value in item.get("possible_questions", [])))
            if not text:
                continue
            key = (text, possible)
            if key in seen:
                continue
            seen.add(key)
            minimal_review.append({"text": text, "possible_questions": list(possible)})

        return ProcessingResult(
            student=student,
            questions=result_questions,
            review=minimal_review,
            unmapped=unmapped_items,
            processed_text=raw_text,
            normalized_text=normalized,
            audit={
                "llm_calls": llm_calls,
                "segmentation_llm_calls": segmentation_llm_calls,
                "mapping_llm_calls": mapping_llm_calls,
                "model": self.llm.model_path,
                "device": self.llm.device or self.llm.device_setting,
                "dtype": getattr(self.llm, "model_dtype", None),
                "quantization": getattr(self.llm, "quantization_mode", "unknown"),
                "exam_id": self.config.exam_id,
                "duration_ms": self.llm.total_duration_ms,
                "candidate_count": len(candidates),
                "accepted_count": len(accepted),
                "block_count": len(blocks),
                "review_count": len(minimal_review),
                "unmapped_count": len(unmapped_items),
            },
        )
=======
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
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
