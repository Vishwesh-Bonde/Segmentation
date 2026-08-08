from __future__ import annotations

import json
from pathlib import Path

from src.config import DEFAULT_CONFIG
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

            logger.info("Cleaning text")
            answers = QuestionSegmenter().segment_text(text)
            logger.info("Finding question numbers")
            logger.info("Questions found : %s", len(answers))
            logger.info("Generating JSON")

            payload = build_student_payload(file_path.stem, answers)
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
