from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvaluationResult:
    question_id: str
    maximum_marks: int | None
    score: int | float | None = None
    correct_concepts: list[str] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    incorrect_concepts: list[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    needs_human_review: bool = False


class AnswerEvaluator:
    """Reserved grading boundary; this stage never allocates marks."""

    def evaluate(self, question_id: str, question: str, model_answer: str, student_answer: str, maximum_marks: int | None) -> EvaluationResult:
        return EvaluationResult(
            question_id,
            maximum_marks,
            reasoning="Evaluation is not implemented in preprocessing.",
            needs_human_review=True,
        )
