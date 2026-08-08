# Answer Segmentation Project

This project reads OCR-extracted plain text files, splits them into question-based answer blocks, and exports each student's answers as a structured JSON file. The project is intentionally limited to the segmentation step of the document-processing pipeline and does not include evaluation, comparison, or AI-based analysis.

## Purpose

The system accepts one text file per student, where each file contains mixed OCR output such as:

```text
Q1 ...
Q2 ...
Q3 ...
```

It then produces a JSON object like:

```json
{
    "student": "student1",
    "answers": {
        "Q1": "Answer text",
        "Q2": "Answer text",
        "Q3": "Answer text"
    }
}
```

## Project structure

```text
project/
    input/
    output/
    logs/
    tests/
    src/
        main.py
        segment.py
        preprocess.py
        regex_patterns.py
        parser.py
        config.py
        utils.py
        logger.py
        exceptions.py
    requirements.txt
    README.md
```

## Installation

```bash
cd project
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Requirements

This project uses only standard Python libraries:

```text
pytest>=8.0.0
```

## How to run

Place OCR text files inside the `input/` folder and start the pipeline:

```bash
cd project
python src/main.py
```

The program will scan every `.txt` file in `input/`, segment answers by question number, and save one JSON file per student in `output/`.

## Input format

Each file should contain plain OCR text. Example:

```text
Q1 Artificial Intelligence is the simulation of human intelligence.
Q2 Machine learning is a subset of AI.
Q3 Deep learning uses neural networks.
```

## Output format

Each generated file is a JSON document with this structure:

```json
{
    "Q1": "Artificial Intelligence is the simulation of human intelligence.",
    "Q2": "Machine learning is a subset of AI.",
    "Q3": "Deep learning uses neural networks."
}
```

If no recognizable question number is present, the system writes:

```json
{
    "UNKNOWN": "Entire OCR Text"
}
```

## Example JSON

```json
{
    "Q1": "Python is a programming language.",
    "Q2": "It supports object-oriented programming.",
    "Q3": "It has a large ecosystem."
}
```

## Notes

- UTF-8 input is supported.
- Hidden and empty files are skipped.
- Duplicate question numbers are merged instead of overwritten.
- The design includes a detector interface, so future detectors can be substituted without changing the segmentation pipeline.
