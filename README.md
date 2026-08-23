# Question-Aware Answer Structuring

This local Python pipeline converts OCR answer-sheet text into auditable, question-aware JSON. It stops before grading: it does not compare model answers, assign marks, calculate scores, use embeddings, or use RAG. Uncertain structure is explicitly routed to human review.

## Architecture

The pipeline is a cascade: conservative normalization, cheap candidate detection, canonical question-paper parsing, deterministic acceptance of strong markers, contextual rejection of weak numeric lists, optional local LLM validation, and auditable review output.

The system accepts one UTF-8 `.txt` file per student in `input/`:

```text
Q1 ...
Q2 ...
Q3 ...
```

It produces one JSON document per student in `output/`:

```json
{
    "student": "student1",
    "processing_status": "success",
    "questions": {"Q1": {"student_answer": {"text": "Answer text"}}},
    "review_items": []
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

The deterministic pipeline uses the standard library. Real local LLM inference uses PyTorch and Hugging Face Transformers:

```text
pytest>=8.0.0
torch>=2.2.0
transformers>=4.40.0
safetensors>=0.4.0
```

## Question paper

Put an optional `question_paper.txt` at the project root. Formats such as `Q1.`, `Question No. 2`, and `1)` are supported, including multiple questions on one line and marks such as `[5 Marks]`, `(10)`, `Marks: 5`, and `5M`. Missing marks remain `null`; they are never guessed.

## How to run

Place OCR text files inside the `input/` folder and start the pipeline:

```bash
cd project
py -m src.main
```

The program scans every `.txt` file independently. A malformed file is logged and does not stop the batch.

## Input format

Each file should contain plain OCR text. Example:

```text
Q1 Artificial Intelligence is the simulation of human intelligence.
Q2 Machine learning is a subset of AI.
Q3 Deep learning uses neural networks.
```

## Output format

Each result retains `raw_text`, `normalized_text`, detected markers, resolved IDs, source offsets, confidence, and status. Canonical questions with no answer have `student_answer: null`. Duplicate or ambiguous blocks are not silently overwritten.

```json
{
    "Q1": "Artificial Intelligence is the simulation of human intelligence.",
    "Q2": "Machine learning is a subset of AI.",
    "Q3": "Deep learning uses neural networks."
}
```

`review_items` can contain `ambiguous_boundary`, `duplicate_question`, `unmapped_answer`, `uncertain_marks`, and other audit reasons. Student-written IDs are preserved separately from resolved IDs.

## Local LLM

The default is deterministic processing with `LLM_ENABLED=false`. To enable actual local inference, install dependencies and download the open-weight Qwen instruct model:

```powershell
py -m pip install -r requirements.txt
py -c "from transformers import AutoTokenizer, AutoModelForCausalLM; p='Qwen/Qwen2.5-1.5B-Instruct'; AutoTokenizer.from_pretrained(p); AutoModelForCausalLM.from_pretrained(p)"
```

For an NVIDIA GPU, install the CUDA-compatible PyTorch wheel from the official PyTorch selector before `transformers`; the client automatically chooses CUDA when available and otherwise uses CPU. Set `LLM_ENABLED=true` and optionally `LLM_MODEL_PATH`, `LLM_DEVICE`, `LLM_MAX_INPUT_TOKENS`, `LLM_MAX_NEW_TOKENS`, and `LLM_TEMPERATURE`. The model is loaded once per process, reused across students, and failures become review items. No cloud inference endpoint is used.

Other controls include `QUESTION_CONFIDENCE_THRESHOLD`, `HUMAN_REVIEW_THRESHOLD`, `MAX_LLM_CONTEXT`, `MAX_LLM_CALLS_PER_DOCUMENT`, and `CACHE_ENABLED`.

The local `model_answers.md` file is loaded as semantic reference data and emitted with each canonical question. It is not used to calculate marks in this stage.

## Testing

```bash
py -m pytest
```

Tests cover years, figures, pages, tables, formulas, numbered answer lists, non-sequential labels, multiline paper questions, marks, and uncertain structure.

## Known limitations

- UTF-8 input is supported.
- Hidden and empty files are skipped.
- OCR with no marker cannot be reliably mapped to a question without semantic evidence; it is reviewed rather than guessed.
- Wrong student markers require stronger question-answer compatibility evidence than this lightweight implementation currently provides.
- A local LLM improves ambiguous interpretation but cannot guarantee correctness. Human review remains part of the workflow.
