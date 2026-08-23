from __future__ import annotations

import json


def mapping_prompt(context: dict[str, object]) -> str:
    return (
        "You are a document-structure classifier, not a grader. Select only a canonical question ID. "
        "Return strict JSON with question_id, confidence, reason, needs_human_review. "
        "Use null when evidence is insufficient. Do not invent IDs.\n\n"
        + json.dumps(context, ensure_ascii=False)
    )
