from __future__ import annotations

import json


def mapping_prompt(context: dict[str, object]) -> str:
    block = str(context.get("student_ocr_block", "")).strip()
    marker = str(context.get("detected_marker") or "").strip()
    ctx = str(context.get("surrounding_context", "")).strip()
    canonical = context.get("canonical_questions") or {}

    canonical_lines: list[str] = []
    for question_id, value in canonical.items():
        if isinstance(value, dict):
            body = value.get("question") or value.get("question_text") or ""
            excerpt = value.get("model_answer_excerpt") or ""
            canonical_lines.append(f"- {question_id}: {body}".strip())
            if excerpt:
                canonical_lines.append(f"  reference: {excerpt[:150]}".strip())
        else:
            canonical_lines.append(f"- {question_id}: {value}".strip())
    canonical_text = "\n".join(canonical_lines) or "None supplied."

    if not marker:
        marker_text = "None"
    else:
        marker_text = f"\"{marker}\""

    if not ctx:
        ctx_text = "None"
    else:
        ctx_text = ctx

    return (
        "Map the complete student OCR block below to one of the supplied canonical questions, "
        "if and only if the block genuinely answers that question.\n\n"
        'Return exactly one JSON object with keys: decision, question_id, confidence, reason, requires_human_review, subject_match.\n'
        "- decision is exactly \"mapped\", \"unmapped\", or \"ambiguous\".\n"
        "- Use \"mapped\" only when the block clearly answers one canonical question AND the subject matches the paper.\n"
        "- Use \"unmapped\" when the block does not answer any canonical question, including when it belongs to a "
        "different subject (for example Java/OOP content when the paper is about Data Structures).\n"
        "- question_id must be one of the supplied canonical IDs (format like \"Q1\") when decision is \"mapped\", else null.\n"
        "- subject_match is true when the block's subject matches the canonical paper, false when it does not, null when unknown.\n"
        "- confidence is a number between 0 and 1; requires_human_review is true or false.\n"
        "- Never invent a question_id. Never rewrite, summarize, or add to the student OCR text.\n"
        "- The same question_id may legitimately be returned for more than one block; duplicate attempts are separate answers.\n\n"
        "Student OCR block:\n"
        + (block or "(empty)") + "\n\n"
        + "Detected marker: " + marker_text + "\n"
        + "Surrounding context: " + ctx_text + "\n\n"
        + "Canonical questions:\n"
        + canonical_text + "\n\n"
        "Return JSON only."
    )