from __future__ import annotations

import json
import re

from src.models import StructuredLLMResult


def coerce_bool_string(value: object) -> bool | None:
    """Coerce a JSON bool, a 'true'/'false' string, or a numeric 1/0 into a bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1 or value == 1.0:
            return True
        if value == 0 or value == 0.0:
            return False
        return None
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned == "true" or cleaned == "1":
            return True
        if cleaned == "false" or cleaned == "0":
            return False
    return None


def coerce_numeric_string(value: object) -> float | None:
    """Coerce a JSON number or a numeric string into a float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        cleaned = value.strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_llm_json(value: str) -> StructuredLLMResult:
    cleaned = value.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = None
        for object_match in re.finditer(r"\{.*?\}", cleaned, flags=re.DOTALL):
            try:
                candidate = json.loads(object_match.group(0))
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and "decision" in candidate:
                data = candidate
                break
        if data is None:
            raise

    requires_human_review = data.get("requires_human_review")
    if requires_human_review is None:
        requires_human_review = data.get("needs_human_review", False)
    requires_human_review = coerce_bool_string(requires_human_review)

    subject_match_value = data.get("subject_match")
    if subject_match_value is None:
        subject_match_value = data.get("subject_compat")
    subject_match = coerce_bool_string(subject_match_value)

    return StructuredLLMResult(
        decision=data.get("decision", "ambiguous"),
        question_id=data.get("question_id"),
        confidence=coerce_numeric_string(data.get("confidence", 0.0)),
        reason=str(data.get("reason", "")),
        requires_human_review=requires_human_review,
        subject_match=subject_match,
        raw_response=value,
    )