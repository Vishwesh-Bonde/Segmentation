from __future__ import annotations


def _format_canonical(questions: dict[str, object]) -> str:
    if not questions:
        return "None supplied."
    lines: list[str] = []
    for question_id, value in questions.items():
        if isinstance(value, dict):
            body = value.get("question") or value.get("question_text") or ""
            excerpt = value.get("model_answer_excerpt") or ""
            lines.append(f"- {question_id}: {body}".strip())
            if excerpt:
                lines.append(f"  reference: {excerpt[:150]}".strip())
        else:
            lines.append(f"- {question_id}: {value}".strip())
    return "\n".join(lines)


def structure_prompt(context: dict[str, object]) -> str:
    operation = context.get("operation")
    candidate = str(context.get("candidate", "")).strip()
    marker = str(context.get("candidate_marker", "")).strip()
    position = context.get("candidate_position")
    count = context.get("candidate_count")
    all_markers = context.get("all_candidate_markers") or []
    preceding = str(context.get("preceding", "")).strip()
    following = str(context.get("following", "")).strip()
    previous = context.get("previous_candidate")
    canonical = context.get("canonical_questions") or {}

    retry_hint = ""
    if operation == "boundary_retry":
        retry_hint = (
            "\nNote: an earlier review judged this marker ambiguous of under-segmentation. "
            "Re-evaluate carefully with the surrounding text."
        )

    previous_hint = ""
    if previous:
        if isinstance(previous, dict):
            previous_hint = (
                f"Previous candidate marker: {previous.get('marker', '')}\n"
                f"Previous candidate line: {previous.get('line', '')}\n"
            )
        else:
            previous_hint = f"Previous candidate marker: {previous}\n"

    return (
        "Classify whether the OCR marker below starts a new top-level answer to a canonical "
        "question or is internal numbered content inside an existing answer.\n\n"
        'Return exactly one JSON object with keys: decision, question_id, confidence, reason, requires_human_review.\n'
        "- decision is exactly \"question_boundary\" or \"continuation\".\n"
        "- A boundary MUST have question_id set to one of the supplied canonical IDs (format like \"Q1\").\n"
        "- For continuation, question_id must be null.\n"
        "- confidence is a number between 0 and 1; requires_human_review is true or false.\n"
        "- Never invent a question ID. Never rewrite the OCR text.\n"
        "- Do not decide from the marker number alone; weigh the surrounding text and canonical questions.\n"
        "- Numbered lists such as \"1. Input\", \"2. Output\", \"1.) Time Complexity\" that are sub-points "
        "of the current answer are almost always \"continuation\".\n\n"
        "Examples:\n"
        "1) marker \"4.\", line \"4. Array An array is a linear data structure that stores\", canonical includes Q4 "
        "\"Explain Array and Linked List.\", fresh paragraph after the Q3 answer => "
        '{"decision":"question_boundary","question_id":"Q4","confidence":0.9,"reason":"New answer numbered 4 matches Q4.","requires_human_review":false}\n'
        "2) marker \"1.\", line \"1. Input: An algorithm may take zero or more inputs.\" appearing after "
        "\"Characteristics of good algorithm\" inside the Q2 answer => "
        '{"decision":"continuation","question_id":null,"confidence":0.9,"reason":"Numbered sub-point inside the Q2 answer.","requires_human_review":false}\n\n'
        "Candidate marker: " + (marker or "(none)") + "\n"
        "Candidate line: " + (candidate or "(empty)") + "\n"
        f"Candidate position: {position} of {count}\n"
        f"All candidate markers in document: {all_markers}\n"
        + previous_hint
        + "Text before (ends at the marker):\n"
        + (preceding or "(empty)") + "\n\n"
        + "Text after (starts after the marker):\n"
        + (following or "(empty)") + "\n\n"
        + "Canonical questions:\n"
        + _format_canonical(canonical) + "\n"
        + retry_hint + "\n\n"
        "Return JSON only."
    )