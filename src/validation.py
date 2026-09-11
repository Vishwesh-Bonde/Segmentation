from __future__ import annotations

import re

from src.llm.schemas import coerce_bool_string, coerce_numeric_string
from src.models import Candidate, StructuredLLMResult

BOUNDARY_DECISIONS = frozenset({"question_boundary", "continuation"})
MAPPING_DECISIONS = frozenset({"mapped", "unmapped", "ambiguous"})


def normalize_question_id(value: object, question_ids: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().upper()
    match = re.fullmatch(r"Q?\s*(\d+)\.?", cleaned)
    if not match:
        return None
    question_id = f"Q{int(match.group(1))}"
    return question_id if question_id in question_ids else None


def validate_llm_result(
    result: StructuredLLMResult,
    question_ids: set[str],
    operation: str = "boundary",
) -> StructuredLLMResult:
    confidence = coerce_numeric_string(result.confidence)
    if confidence is None:
        result.confidence = 0.0
        result.reason = "LLM returned a nonnumeric confidence."
        result.requires_human_review = True
    else:
        result.confidence = max(0.0, min(1.0, confidence))

    if operation in {"boundary", "boundary_retry"}:
        valid_decisions = BOUNDARY_DECISIONS
    else:
        valid_decisions = MAPPING_DECISIONS

    if result.decision not in valid_decisions:
        result.decision = "ambiguous"
        result.reason = "LLM returned an invalid decision."
        result.requires_human_review = True

    if result.question_id is not None:
        normalized_id = normalize_question_id(result.question_id, question_ids)
        if normalized_id is None:
            result.question_id = None
            result.reason = "LLM returned an unknown question ID."
            result.requires_human_review = True
        else:
            result.question_id = normalized_id

    if result.requires_human_review is None:
        result.requires_human_review = False
    elif not isinstance(result.requires_human_review, bool):
        result.requires_human_review = True
        result.reason = "LLM returned a non-boolean review flag."

    if result.subject_match is not None and not isinstance(result.subject_match, bool):
        result.subject_match = None

    if result.decision == "question_boundary" and result.question_id is None:
        result.requires_human_review = True
    if result.decision == "mapped" and result.question_id is None:
        result.requires_human_review = True
    if result.decision == "mapped" and result.subject_match is False:
        result.decision = "ambiguous"
        result.reason = "LLM mapped content that it also flagged as subject-mismatched."
        result.requires_human_review = True

    if result.decision == "ambiguous":
        result.requires_human_review = True
    return result


def candidate_is_safe(candidate: Candidate, known_ids: set[str], current_question: str | None) -> bool:
    if candidate.strength == "weak":
        return False
    if candidate.strength == "strong":
        return candidate.number is not None and f"Q{candidate.number}" in known_ids
    if candidate.number is None or f"Q{candidate.number}" not in known_ids:
        return False
    return current_question is None