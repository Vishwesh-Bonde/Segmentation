from __future__ import annotations


def structure_prompt(context: dict[str, object]) -> str:
    return """Return only strict JSON with keys decision, question_id, confidence, reason, requires_human_review.\nAllowed decisions: question_boundary, continuation, subquestion, ordinary_content, header_footer, unmapped, ambiguous.\nNever invent a question ID. This is structural analysis, not grading.\n\nContext:\n""" + str(context)
