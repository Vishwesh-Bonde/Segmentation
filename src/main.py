from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path

from src.config import DEFAULT_CONFIG
from src.answer_processor import AnswerProcessor
from src.question_paper import load_question_paper
from src.model_answers import load_model_answers
from src.logger import configure_logger
from src.segment import QuestionSegmenter


def build_student_payload(student_name: str, answers: dict[str, str]) -> dict[str, object]:
    return {"student": student_name, "answers": answers}


def process_all_files() -> list[Path]:
    config = DEFAULT_CONFIG
    logger = configure_logger(config.logs_dir)
    input_dir = config.input_dir
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)

    processed_files: list[Path] = []
    questions = load_question_paper(config.question_paper_path)
    model_answers = load_model_answers(config.model_answers_path)
    questions = {key: replace(question, model_answer=model_answers.get(key)) for key, question in questions.items()}
    processor = AnswerProcessor(config)

    for file_path in sorted(input_dir.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() != ".txt":
            continue
        if file_path.name.startswith("."):
            continue

        logger.info("Reading %s", file_path.name)

        try:
            text = file_path.read_text(encoding="utf-8")
            if not text.strip():
                logger.warning("Skipping empty file: %s", file_path.name)
                continue

            logger.info("Structuring OCR text")
            structured = processor.process(file_path.stem, text, questions, config.question_paper_path.name if config.question_paper_path else None)
            logger.info("Questions found: %s; review items: %s", len(structured.questions), len(structured.review_items))
            payload = asdict(structured)
            output_path = output_dir / f"{file_path.stem}.json"
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
            processed_files.append(file_path)
            logger.info("Completed")
        except (UnicodeDecodeError, OSError):
            logger.exception("Failed to process %s", file_path.name)
            continue

    return processed_files


if __name__ == "__main__":
    process_all_files()
