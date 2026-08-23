from src.answer_processor import AnswerProcessor
from src.config import DEFAULT_CONFIG
from src.question_paper import parse_question_paper
from src.llm.client import LocalLLMClient
from src.models import StructuredLLMResult


PAPER = parse_question_paper("1. Define Python. [5 Marks] 2. Explain algorithms. [5] 4. Explain lists. [10]")


def process(text):
    return AnswerProcessor(DEFAULT_CONFIG).process("student", text, PAPER, "question_paper.txt")


def test_year_and_numbered_list_stay_in_answer():
    result = process("Q1. Python was released in 1991.\n1. Input\n2. Output\nQ2. Algorithms are finite.")
    answer = result.questions["Q1"]["student_answer"]["text"]
    assert "1991" in answer
    assert "1. Input" in answer
    assert "Q1991" not in result.questions


def test_non_sequential_markers_are_preserved():
    result = process("Q1. Python answer.\nQ4. List answer.\nQ2. Algorithm answer.")
    answers = [item["student_answer"] for item in result.questions.values() if item["student_answer"]]
    assert [answer["detected_marker"] for answer in sorted(answers, key=lambda value: value["source_order"])] == ["Q1", "Q4", "Q2"]


def test_paper_marks_and_multiline_text():
    questions = parse_question_paper("Q4. Explain the architecture of a computer\nsystem. [10 Marks]")
    assert questions["Q4"].max_marks == 10
    assert questions["Q4"].question_text == "Explain the architecture of a computer system."


def test_page_figure_table_do_not_create_boundaries():
    result = process("Python was created in 1991.\nFigure 3.2 shows it.\nTable 4.1 contains data.\nPage 12.")
    assert not result.questions["Q1"]["student_answer"]
    assert result.review_items


def test_model_answer_headings_are_canonical_questions():
    questions = parse_question_paper("## Q1. Explain data structures. [10 Marks]\n\nA data structure is a way of organizing data.\n\n## Q2. Define an algorithm. [10 Marks]")
    assert list(questions) == ["Q1", "Q2"]
    assert questions["Q1"].question_text == "Explain data structures."
    assert questions["Q1"].max_marks == 10


def test_disabled_llm_is_explicit_review_fallback():
    client = LocalLLMClient(DEFAULT_CONFIG)
    result = client.analyze_structure({"canonical_questions": {"Q1": "Define Python"}, "student": "text"})
    assert isinstance(result, StructuredLLMResult)
    assert result.requires_human_review is True


def test_invalid_llm_json_is_rejected():
    from src.llm.schemas import parse_llm_json
    import pytest
    with pytest.raises(ValueError):
        parse_llm_json("not json")
