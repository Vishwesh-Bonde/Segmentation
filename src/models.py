from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Question:
    question_id: str
    number: int
    question_text: str
    max_marks: int | None = None
    model_answer: str | None = None
    model_answer: str | None = None


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
    question_paper: str | None
    questions: dict[str, dict[str, object]]
    unmapped_content: list[dict[str, object]] = field(default_factory=list)
    review_items: list[dict[str, object]] = field(default_factory=list)
    processing_status: str = "success"
    raw_text: str = ""
    normalized_text: str = ""
