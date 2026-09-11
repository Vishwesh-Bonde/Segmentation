from src.answer_processor import AnswerProcessor
from src.config import Config, DEFAULT_CONFIG
from src.question_paper import parse_question_paper
from src.llm.client import LocalLLMClient
from src.model_answers import load_model_answers, parse_model_answers
import json
from dataclasses import replace
from pathlib import Path

from src.models import Candidate, StructuredLLMResult
from src.preprocess import normalize_text
from src.validation import candidate_is_safe, normalize_question_id, validate_llm_result


def test_llm_is_enabled_by_default():
    assert DEFAULT_CONFIG.llm_enabled is True
    project_defaults = Config.from_project_root(Path.cwd())
    assert project_defaults.model_path == "ibm-granite/granite-3.3-2b-instruct"
    assert project_defaults.quantization_4bit is True


class FakeSemanticLLM:
    model_path = "fake"
    device = "cpu"
    device_setting = "cpu"
    total_duration_ms = 0

    def __init__(self):
        self.calls = []

    def analyze_structure(self, context):
        self.calls.append(context)
        if context.get("operation") in {"boundary", "boundary_retry"}:
            marker = str(context.get("candidate_marker", ""))
            line = str(context.get("candidate", "")).lower()
            is_explicit = marker.lower().startswith(("q", "question"))
            is_weak_question = "→" in marker and any(word in line for word in ("data structure", "algorithm"))
            if is_explicit or is_weak_question:
                return StructuredLLMResult("question_boundary", None, 0.99, "semantic boundary")
            return StructuredLLMResult("continuation", None, 0.99, "internal answer numbering")

        text = str(context.get("student_ocr_block", "")).lower()
        if "complexity" in text:
            question_id = "Q3"
        elif "algorithm" in text:
            question_id = "Q2"
        elif "difference between array and linked list" in text or "nodes are accessed" in text:
            question_id = "Q4"
        elif "list answer" in text:
            question_id = "Q4"
        elif "data structure" in text or "python" in text or "array" in text or "list answer" in text:
            question_id = "Q1"
        else:
            return StructuredLLMResult("ambiguous", None, 0.0, "insufficient evidence", True)
        return StructuredLLMResult("mapped", question_id, 0.99, "semantic mapping", False, True)


class StudentFiveSemanticLLM:
    model_path = "fake"
    device = "cpu"
    device_setting = "cpu"
    total_duration_ms = 0
    model_dtype = "float32"
    quantization_mode = "none"

    def __init__(self):
        self.boundary_decisions = iter((True, True, False, False, True, False, False, True))
        self.boundary_ids = iter(("Q1", "Q2", None, None, "Q3", None, None, "Q4"))
        self.mapping_number = 0

    def analyze_structure(self, context):
        if context.get("operation") in {"boundary", "boundary_retry"}:
            decision = next(self.boundary_decisions)
            question_id = next(self.boundary_ids)
            return StructuredLLMResult(
                "question_boundary" if decision else "continuation",
                question_id,
                0.99,
                "test semantic boundary decision",
            )

        self.mapping_number += 1
        return StructuredLLMResult(
            "mapped",
            f"Q{self.mapping_number}",
            0.99,
            "test semantic mapping",
            False,
            True,
        )


PAPER = parse_question_paper("1. Define Python. [5 Marks] 2. Explain algorithms. [5] 4. Explain lists. [10]")


def process(text):
    return AnswerProcessor(DEFAULT_CONFIG, llm=FakeSemanticLLM()).process("student", text, PAPER, "question_paper.txt")


def test_year_and_numbered_list_stay_in_answer():
    result = process("Q1. Python was released in 1991. It is readable.\n1. Input\nQ2. Algorithms are finite.")
    answer = result.questions["Q1"]
    assert isinstance(answer, str)
    assert "1991" in answer
    assert "1. Input" in answer
    assert "Q1991" not in answer


def test_non_sequential_markers_are_preserved():
    result = process("Q1. Python answer.\nQ4. List answer.\nQ2. Algorithm answer.")
    answered = {question_id for question_id, value in result.questions.items() if value is not None}
    assert answered == {"Q1", "Q2", "Q4"}


def test_paper_marks_and_multiline_text():
    questions = parse_question_paper("Q4. Explain the architecture of a computer\nsystem. [10 Marks]")
    assert questions["Q4"].max_marks == 10
    assert questions["Q4"].question_text == "Explain the architecture of a computer system."


def test_page_figure_table_do_not_create_boundaries():
    result = process("Python was created in 1991.\nFigure 3.2 shows it.\nTable 4.1 contains data.\nPage 12.")
    assert "Figure 3.2" in str(result.questions["Q1"])
    assert result.review == []


def test_model_answer_headings_are_canonical_questions():
    questions = parse_question_paper("## Q1. Explain data structures. [10 Marks]\n\nA data structure is a way of organizing data.\n\n## Q2. Define an algorithm. [10 Marks]")
    assert list(questions) == ["Q1", "Q2"]
    assert questions["Q1"].question_text == "Explain data structures."
    assert questions["Q1"].max_marks == 10


def test_disabled_llm_is_explicit_review_fallback():
    client = LocalLLMClient(replace(DEFAULT_CONFIG, llm_enabled=False))
    result = client.analyze_structure({"canonical_questions": {"Q1": "Define Python"}, "student": "text"})
    assert isinstance(result, StructuredLLMResult)
    assert result.requires_human_review is True


def test_model_answers_are_the_single_source_of_truth():
    questions = parse_model_answers(DEFAULT_CONFIG.model_answers_path)
    assert list(questions)[:4] == ["Q1", "Q2", "Q3", "Q4"]
    assert questions["Q1"].question_text.startswith("Explain Data Structures")
    assert questions["Q2"].question_text.startswith("Define an Algorithm")
    assert questions["Q1"].model_answer and "Data structures are broadly classified" in questions["Q1"].model_answer

    model_answers = load_model_answers(DEFAULT_CONFIG.model_answers_path)
    assert "Q1" in model_answers and "Q2" in model_answers and "Q4" in model_answers


def test_invalid_llm_json_is_rejected():
    from src.llm.schemas import parse_llm_json
    import pytest
    with pytest.raises(ValueError):
        parse_llm_json("not json")


def test_nonnumeric_confidence_is_reviewable():
    result = StructuredLLMResult(
        "question_boundary",
        "Q1",
        "high",
        "invalid confidence",
    )

    validated = validate_llm_result(result, {"Q1"})

    assert validated.confidence == 0.0
    assert validated.requires_human_review is True


def test_supported_string_confidence_and_boolean_are_coerced():
    from src.llm.schemas import parse_llm_json

    result = parse_llm_json(
        '{"decision":"question_boundary","question_id":"Q1",'
        '"confidence":"high","reason":"short",'
        '"requires_human_review":"false"}'
    )

    validated = validate_llm_result(result, {"Q1"})

    assert validated.confidence == 0.0
    assert validated.requires_human_review is True


def test_granite_internal_decision_is_rejected():
    result = validate_llm_result(
        StructuredLLMResult("internal", "Q2", 0.95, "internal point"),
        {"Q1", "Q2"},
    )

    assert result.decision == "ambiguous"
    assert result.requires_human_review is True


def test_weak_numeric_sections_are_not_auto_accepted():
    weak_candidate = Candidate("1→", 1, 0, 3, "weak", "1→ A data structure")
    assert candidate_is_safe(weak_candidate, {"Q1", "Q2", "Q3", "Q4"}, None) is False


def test_identifier_format_variants_are_normalized_only_against_canonical_ids():
    ids = {"Q1", "Q4"}

    assert normalize_question_id("1", ids) == "Q1"
    assert normalize_question_id("4.", ids) == "Q4"
    assert normalize_question_id("Q1.", ids) == "Q1"
    assert normalize_question_id("Q9", ids) is None


def test_continuation_with_question_id_is_not_a_boundary():
    result = validate_llm_result(
        StructuredLLMResult("continuation", "Q4", 0.99, "internal point"),
        {"Q1", "Q4"},
    )

    assert result.decision == "continuation"


def test_boundary_llm_call_receives_context():
    class ContextLLM(FakeSemanticLLM):
        def __init__(self):
            super().__init__()
            self.boundary_contexts = []

        def analyze_structure(self, context):
            if context.get("operation") == "boundary":
                self.boundary_contexts.append(context)
            return super().analyze_structure(context)

    fake = ContextLLM()
    AnswerProcessor(DEFAULT_CONFIG, llm=fake).process(
        "student",
        "Q1. First answer.\n4. Sub-point that falls outside the next fill order.\nQ2. Second answer.\nQ4. Fourth answer.",
        PAPER,
    )

    assert fake.boundary_contexts
    assert any(
        ctx["preceding"] or ctx["following"]
        for ctx in fake.boundary_contexts
    )


def test_continuation_preserves_complete_marker_text():
    class MarkerLLM(FakeSemanticLLM):
        def analyze_structure(self, context):
            if context.get("operation") in {"boundary", "boundary_retry"}:
                return StructuredLLMResult("continuation", None, 0.99, "internal content")
            return StructuredLLMResult("mapped", "Q1", 0.99, "mapped", False, True)

    result = AnswerProcessor(
        DEFAULT_CONFIG,
        llm=MarkerLLM(),
    ).process(
        "student",
        "Q1. Parent answer\n1.) Time Complexity\nQ2. Next answer",
        PAPER,
    )

    assert any(
        "1.) Time Complexity" in str(answer)
        for answer in result.questions.values()
    )


def test_complete_student_8_flow_maps_four_answers_and_invokes_mapping():
    text = Path("input/student_8.txt").read_text(encoding="utf-8")
    fake = FakeSemanticLLM()
    result = AnswerProcessor(DEFAULT_CONFIG, llm=fake).process(
        "student_8", text, parse_model_answers(DEFAULT_CONFIG.model_answers_path)
    )

    assert all(result.questions[question_id] for question_id in ("Q1", "Q2", "Q3", "Q4"))
    assert result.questions["Q1"] is not None
    assert "data structure" in str(result.questions["Q1"]).lower()
    assert "array" in str(result.questions["Q4"]).lower()
    assert result.audit["segmentation_llm_calls"] == 0
    assert result.audit["mapping_llm_calls"] == 5
    assert result.unmapped == []


def test_internal_numbered_lists_remain_inside_one_answer_block():
    result = process("Q1. Define Python.\nQ2. Data structures include:\n1. Array\n2. Linked List\n3. Stack")

    merged = "\n".join(
        value if isinstance(value, str) else "\n".join(value)
        for value in result.questions.values()
        if value is not None
    )
    assert "1. Array" in merged
    assert "2. Linked List" in merged
    assert "3. Stack" in merged
    assert result.review == []


def test_duplicate_attempts_are_preserved_as_a_list():
    result = process("Q1. First Python answer.\nQ1. Second Python answer.")

    assert result.questions["Q1"] == ["First Python answer.", "Second Python answer."]
    assert result.review == []


def test_ambiguous_and_unmapped_content_are_not_silently_assigned():
    fake = FakeSemanticLLM()
    result = AnswerProcessor(DEFAULT_CONFIG, llm=fake).process(
        "student", "This content has no canonical evidence.", PAPER
    )

    assert result.questions == {"Q1": None, "Q2": None, "Q4": None}
    assert result.review
    assert result.unmapped == ["This content has no canonical evidence."]


def test_production_json_uses_only_final_segmentation_schema():
    result = process("Q1. First Python answer.\nQ1. Second Python answer.")
    payload = result.to_minimal_json()

    assert set(payload) == {"student_id", "exam_id", "answers", "unmapped_content"}
    assert payload["student_id"] == "student"
    assert payload["answers"] == [
        {"question_id": "Q1", "answer": "First Python answer."},
        {"question_id": "Q1", "answer": "Second Python answer."},
    ]
    assert payload["unmapped_content"] == []


def test_production_json_preserves_unmapped_content_as_objects():
    result = process("Q1. Python answer.")
    result.unmapped.append("unassigned OCR text")

    assert result.to_minimal_json()["unmapped_content"] == [{"text": "unassigned OCR text"}]


def test_configured_exam_id_is_emitted_in_production_json():
    config = replace(DEFAULT_CONFIG, exam_id="ML_2026_SEM5")
    result = AnswerProcessor(config, llm=FakeSemanticLLM()).process(
        "student_01", "Q1. Python answer.", PAPER
    )

    assert result.to_minimal_json()["exam_id"] == "ML_2026_SEM5"


def test_known_generation_artifacts_are_removed_without_rewriting_ocr():
    normalized = normalize_text(
        "Answer <s> before <|im_ start <|endoftext|>\nAnswer </s> after <|im_end|> "
        "<|assistant|> text <|user|>"
    )

    assert "<|im_" not in normalized
    assert "<|assistant|>" not in normalized
    assert "<|user|>" not in normalized
    assert "<|endoftext|>" not in normalized
    assert "<s>" not in normalized
    assert "</s>" not in normalized
    assert "Answer before" in normalized
    assert "Answer after" in normalized


def test_student_5_regression_keeps_internal_numbering_inside_q2_and_q3():
    text = Path("input/student_5.txt").read_text(encoding="utf-8")
    result = AnswerProcessor(
        DEFAULT_CONFIG,
        llm=StudentFiveSemanticLLM(),
    ).process(
        "student_5",
        text,
        parse_model_answers(DEFAULT_CONFIG.model_answers_path),
    )
    payload = result.to_minimal_json()

    assert [answer["question_id"] for answer in payload["answers"]] == [
        "Q1",
        "Q2",
        "Q3",
        "Q4",
    ]
    q2 = next(answer["answer"] for answer in payload["answers"] if answer["question_id"] == "Q2")
    q3 = next(answer["answer"] for answer in payload["answers"] if answer["question_id"] == "Q3")
    assert "1. Input" in q2
    assert "2. Output" in q2
    assert "1.) Time Complexity" in q3
    assert "2.) Space Complexity" in q3
    assert "<|im_" not in json.dumps(payload)
    assert set(payload) == {"student_id", "exam_id", "answers", "unmapped_content"}
    assert result.audit["segmentation_llm_calls"] == 0


def test_suspicious_single_block_is_not_silently_mapped_to_q1():
    text = Path("input/student_6.txt").read_text(encoding="utf-8")
    result = AnswerProcessor(
        DEFAULT_CONFIG,
        llm=FakeSemanticLLM(),
    ).process(
        "student_6",
        text,
        parse_model_answers(DEFAULT_CONFIG.model_answers_path),
    )
    payload = result.to_minimal_json()

    assert payload["answers"] == []
    assert payload["unmapped_content"]
    assert len(result.unmapped) == 1
    assert result.review


def test_mapping_subject_mismatch_is_rejected():
    validated = validate_llm_result(
        StructuredLLMResult("mapped", "Q1", 0.98, "subject mismatch", False, False),
        {"Q1", "Q2"},
        operation="mapping",
    )

    assert validated.decision == "ambiguous"
    assert validated.requires_human_review is True


def test_mapping_legacy_vocabulary_is_rejected():
    validated = validate_llm_result(
        StructuredLLMResult("question_boundary", "Q1", 0.98, "old attempt vocabulary"),
        {"Q1", "Q2"},
        operation="mapping",
    )

    assert validated.decision == "ambiguous"
    assert validated.requires_human_review is True


def test_numeric_subject_match_is_coerced_to_true():
    from src.llm.schemas import parse_llm_json

    result = parse_llm_json(
        '{"decision":"mapped","question_id":"Q1","confidence":0.95,'
        '"reason":"matches","subject_match":1}'
    )

    assert result.subject_match is True
    assert result.confidence == 0.95


def test_internal_numbered_list_that_reach_next_ordinal_stay_inside_answer():
    result = process(
        "Q1. Explain data structures.\n"
        "A data structure is a way of organizing data. It has:\n"
        "1. Linear data structures - arrays.\n"
        "2. Non-Linear data structures - trees.\n"
        "3. Operations: traversal, insertion, deletion.\n"
        "4. Examples: stack, queue.\n"
        "Q2. Define an algorithm.\n"
        "An algorithm is a finite set of steps.\n"
        "1. Finiteness\n"
        "2. Definiteness\n"
        "Q4. List answer."
    )

    q1 = str(result.questions["Q1"])
    assert "1. Linear data structures" in q1
    assert "4. Examples: stack, queue." in q1
    assert "Q2" in result.questions
    q2 = str(result.questions["Q2"])
    assert "1. Finiteness" in q2
    assert result.review == []


def test_out_of_order_weak_marker_in_numbered_run_stays_inside_answer():
    class RunAwareLLM(FakeSemanticLLM):
        def __init__(self):
            super().__init__()
            self.boundary_calls = 0

        def analyze_structure(self, context):
            if context.get("operation") == "boundary":
                self.boundary_calls += 1
            return super().analyze_structure(context)

    text = (
        "Q1. Explain data structures.\n"
        "1. Primitive data structures.\n"
        "2. Non-primitive data structures.\n"
        "3. Operations.\n"
        "4. Examples.\n"
        "5. Applications.\n"
        "Q2. Define an algorithm.\n"
        "An algorithm is a finite set of steps.\n"
        "1. Finiteness\n"
        "2. Definiteness\n"
        "Q4. List answer."
    )
    fake = RunAwareLLM()
    result = AnswerProcessor(DEFAULT_CONFIG, llm=fake).process("student", text, PAPER)

    q1 = str(result.questions["Q1"])
    assert "1. Primitive data structures" in q1
    assert "4. Examples." in q1
    assert "5. Applications." in q1
    q2 = str(result.questions["Q2"])
    assert "1. Finiteness" in q2
    assert "2. Definiteness" in q2
    assert result.questions["Q4"] is not None
    assert result.review == []
    assert fake.boundary_calls == 0


def test_out_of_order_marker_outside_numbered_run_still_goes_to_llm():
    class ContextLLM(FakeSemanticLLM):
        def __init__(self):
            super().__init__()
            self.boundary_calls = 0

        def analyze_structure(self, context):
            if context.get("operation") == "boundary":
                self.boundary_calls += 1
            return super().analyze_structure(context)

    fake = ContextLLM()
    AnswerProcessor(DEFAULT_CONFIG, llm=fake).process(
        "student",
        "Q1. First answer.\n4. Lone sub-point with no sibling numbering.\nQ2. Second answer.\nQ4. Fourth answer.",
        PAPER,
    )

    assert fake.boundary_calls >= 1


def test_adjacent_weak_same_question_blocks_are_merged():
    class MergeAwareLLM(FakeSemanticLLM):
        def analyze_structure(self, context):
            if context.get("operation") in {"boundary", "boundary_retry"}:
                return super().analyze_structure(context)
            text = str(context.get("student_ocr_block", ""))
            if "Size" in text and "fixed" in text:
                return StructuredLLMResult("mapped", "Q4", 0.99, "array size section", False, True)
            return super().analyze_structure(context)

    result = AnswerProcessor(DEFAULT_CONFIG, llm=MergeAwareLLM()).process(
        "student_8",
        Path("input/student_8.txt").read_text(encoding="utf-8"),
        parse_model_answers(DEFAULT_CONFIG.model_answers_path),
    )

    q4 = result.questions["Q4"]
    assert isinstance(q4, str)
    assert "► Array" in q4
    assert "Size" in q4
    assert result.unmapped == []
