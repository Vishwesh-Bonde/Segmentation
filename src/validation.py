from __future__ import annotations

from src.models import Candidate, StructuredLLMResult


def validate_llm_result(result: StructuredLLMResult, question_ids: set[str]) -> StructuredLLMResult:
    result.confidence = max(0.0, min(1.0, float(result.confidence)))
    valid_decisions = {"question_boundary", "continuation", "subquestion", "ordinary_content", "header_footer", "unmapped", "ambiguous"}
    if result.decision not in valid_decisions:
        result.decision = "ambiguous"
        result.reason = "LLM returned an invalid decision."
        result.requires_human_review = True
    if result.question_id is not None and result.question_id not in question_ids:
        result.question_id = None
        result.reason = "LLM returned an unknown question ID."
        result.requires_human_review = True
    if result.decision == "ambiguous":
        result.requires_human_review = True
    return result


def candidate_is_safe(candidate: Candidate, known_ids: set[str], current_question: str | None) -> bool:
    if candidate.strength == "strong":
        return candidate.number is not None and f"Q{candidate.number}" in known_ids
    if candidate.number is None or f"Q{candidate.number}" not in known_ids:
        return False
    return current_question is None
