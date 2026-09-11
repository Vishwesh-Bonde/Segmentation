from __future__ import annotations

from src.llm.client import LocalLLMClient
from src.models import Question, StructuredLLMResult
from src.validation import validate_llm_result


class SemanticQuestionMapper:
    """Maps one already-segmented OCR block to the canonical paper via the local LLM."""

    def __init__(self, client: LocalLLMClient) -> None:
        self.client = client

    def map_block(self, text: str, questions: dict[str, Question], detected_marker: str | None = None, surrounding_context: str = "") -> StructuredLLMResult:
        result = self.client.analyze_structure({
            "operation": "mapping",
            "canonical_questions": {
                key: {
                    "question": question.question_text,
                    "model_answer_excerpt": (question.model_answer or "")[:150],
                }
                for key, question in questions.items()
            },
            "student_ocr_block": text,
            "detected_marker": detected_marker,
            "surrounding_context": surrounding_context,
        })
        return validate_llm_result(result, set(questions), operation="mapping")
