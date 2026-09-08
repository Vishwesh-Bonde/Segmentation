from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Question:
    question_id: str
    number: int
    question_text: str
    max_marks: int | None = None
    model_answer: str | None = None
<<<<<<< HEAD
=======
    model_answer: str | None = None
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5


@dataclass(frozen=True)
class Candidate:
    marker: str
    number: int | None
    start: int
    end: int
    strength: str
    line_text: str


@dataclass
class StructuredLLMResult:
    decision: str
    question_id: str | None
    confidence: float
    reason: str
    requires_human_review: bool = False
<<<<<<< HEAD
    subject_match: bool | None = None
=======
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
    raw_response: str | None = None


@dataclass
class AnswerBlock:
    text: str
    source_start: int
    source_end: int
    detected_marker: str | None = None
    resolved_question_id: str | None = None
    confidence: float = 0.0
    status: str = "needs_human_review"
    source_order: int = 0


@dataclass
class ProcessingResult:
    student: str
<<<<<<< HEAD
    questions: dict[str, str | list[str] | None]
    review: list[dict[str, object]] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    processed_text: str = ""
    normalized_text: str = ""
    audit: dict[str, object] = field(default_factory=dict)

    @property
    def student_id(self) -> str:
        return self.student

    @property
    def review_items(self) -> list[dict[str, object]]:
        return self.review

    @property
    def unmapped_content(self) -> list[str]:
        return self.unmapped

    @property
    def processing_status(self) -> str:
        return "success"

    def to_minimal_json(self) -> dict[str, object]:
        answers: list[dict[str, str]] = []
        for question_id, value in self.questions.items():
            if value is None:
                continue
            values = value if isinstance(value, list) else [value]
            answers.extend(
                {"question_id": question_id, "answer": answer}
                for answer in values
            )

        return {
            "student_id": self.student,
            "exam_id": str(self.audit.get("exam_id", "")),
            "answers": answers,
            "unmapped_content": [{"text": text} for text in self.unmapped],
        }

    def to_debug_json(self) -> dict[str, object]:
        return {
            "student": self.student,
            "questions": self.questions,
            "review": self.review,
            "unmapped": self.unmapped,
            "audit": self.audit,
            "processed_text": self.processed_text,
            "normalized_text": self.normalized_text,
        }
=======
    question_paper: str | None
    questions: dict[str, dict[str, object]]
    unmapped_content: list[dict[str, object]] = field(default_factory=list)
    review_items: list[dict[str, object]] = field(default_factory=list)
    processing_status: str = "success"
    raw_text: str = ""
    normalized_text: str = ""
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
