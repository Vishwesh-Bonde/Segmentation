from __future__ import annotations

import json

from src.models import StructuredLLMResult


def parse_llm_json(value: str) -> StructuredLLMResult:
    data = json.loads(value)
    return StructuredLLMResult(
        decision=data.get("decision", "ambiguous"),
        question_id=data.get("question_id"),
        confidence=data.get("confidence", 0.0),
        reason=str(data.get("reason", "")),
        requires_human_review=bool(data.get("requires_human_review", False)),
        raw_response=value,
    )
