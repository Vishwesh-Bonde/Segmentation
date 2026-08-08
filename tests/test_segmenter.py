from src.segment import QuestionSegmenter, RegexQuestionDetector


def build_segmenter():
    return QuestionSegmenter(detector=RegexQuestionDetector())


def test_perfect_ocr():
    text = """Q1 Python is a programming language.
Q2 It supports object-oriented programming.
Q3 It has a large ecosystem."""

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "Python is a programming language.",
        "Q2": "It supports object-oriented programming.",
        "Q3": "It has a large ecosystem.",
    }


def test_extra_blank_lines():
    text = """Q1 First answer.


Q2 Second answer.


Q3 Third answer."""

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "First answer.",
        "Q2": "Second answer.",
        "Q3": "Third answer.",
    }


def test_missing_blank_lines():
    text = """Q1 This is answer one.
This continues on next line.
Q2 This is answer two.
It also continues."""

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "This is answer one. This continues on next line.",
        "Q2": "This is answer two. It also continues.",
    }


def test_question_and_answer_on_same_line():
    text = "Q3 Explain AI. Artificial Intelligence is the simulation of human intelligence."

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q3": "Artificial Intelligence is the simulation of human intelligence.",
    }


def test_question_on_separate_line():
    text = """Q4
Explain machine learning.
It is a subset of AI."""

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q4": "Explain machine learning. It is a subset of AI.",
    }


def test_duplicate_question_numbers_are_merged():
    text = """Q1 First answer.
Q1 Second answer.
Q2 Final answer."""

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "First answer. Second answer.",
        "Q2": "Final answer.",
    }


def test_unknown_question():
    text = """This file has no question markers.
It contains plain OCR text only."""

    result = build_segmenter().segment_text(text)

    assert result == {"UNKNOWN": "This file has no question markers. It contains plain OCR text only."}


def test_only_one_question():
    text = "Q7 Answer text only once."

    result = build_segmenter().segment_text(text)

    assert result == {"Q7": "Answer text only once."}


def test_many_questions():
    lines = [f"Q{i} Answer {i}" for i in range(1, 11)]
    text = "\n".join(lines)

    result = build_segmenter().segment_text(text)

    assert len(result) == 10
    assert result["Q10"] == "Answer 10"


def test_single_line_ocr_paragraph():
    text = "Q1 Python is a programming language. Q2 Data structures help organize data. Q3 OS manages resources. Q4 Physics explains motion."

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "Python is a programming language.",
        "Q2": "Data structures help organize data.",
        "Q3": "OS manages resources.",
        "Q4": "Physics explains motion.",
    }


def test_missing_question_numbers_still_segment():
    text = "Q1 First answer. Q3 Third answer. Q5 Fifth answer."

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "First answer.",
        "Q3": "Third answer.",
        "Q5": "Fifth answer.",
    }


def test_ocr_formatting_errors_and_mixed_whitespace():
    text = "Q l  Explain AI.\tQI  Data Structures are useful.\nQ.  Operating systems manage hardware.\nQ-    Physics studies motion."

    result = build_segmenter().segment_text(text)

    assert result == {
        "Q1": "Explain AI.",
        "Q2": "Data Structures are useful.",
        "Q3": "Operating systems manage hardware.",
        "Q4": "Physics studies motion.",
    }


def test_empty_file():
    result = build_segmenter().segment_text("")

    assert result == {"UNKNOWN": "Entire OCR Text"}
