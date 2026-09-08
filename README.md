# Question-Aware Answer Structuring

<<<<<<< HEAD
A local Python pipeline that converts OCR'd student answer-sheet text into auditable, question-aware JSON. The pipeline **stops before grading**: it does not assign marks, compare model answers for scoring, use embeddings, or use RAG. Anything it cannot map safely is preserved in `unmapped_content` and flagged in `output/debug/` rather than guessed or dropped.

## What it does

- Reads one UTF-8 `.txt` file per student from `input/`.
- Loads the canonical questions from `model_answers.md` (the single source of truth — question meanings are never hardcoded).
- Segments each document into per-question answer blocks using a **deterministic structural classifier** that understands exam markers (`Q1`, `Q2)`, `Q3.`), OCR numbering noise, and internal numbered lists.
- Uses a **local small LLM** only for genuinely ambiguous segmentation and for mapping blocks to questions. Mapping is only accepted behind a strict gate (`decision == "mapped"`, canonical `question_id`, `subject_match == True`, `confidence >= 0.85`, no human-review flag).
- Writes one minimal JSON per student to `output/`, plus a full debug/audit JSON to `output/debug/`.

## Pipeline (how it decides)

1. **Normalize & clean** — collapse whitespace, strip OCR/LLM artifacts (`<|im_start|>`, `<|endoftext|>`, `</s>`, …).
2. **Detect markers** — two families:
   - *Strong* (`Q1`, `Question 1`, `Q. 4`): accepted immediately.
   - *Weak* (`1.`, `2)`, `①`, `1→`): resolved against the canonical question order.
3. **Classify weak markers deterministically**:
   - `index < next-unanswered-ordinal` → continuation (stays in the current block).
   - `index == next-ordinal` in document order → boundary.
   - **Suppression**: a weak marker is ignored if the same number repeats later (internal lists repeat numbers; question markers don't), so `2. Non-Primitive` inside Q1 never becomes a Q2 boundary.
   - **Numbered-run rule**: an out-of-order weak marker whose immediate successor is another weak marker numbered `+1` (e.g. `4. … 5. … 6. …`) is treated as continuation — consecutive runs are internal lists, not questions.
   - Meaningful text before the first marker implies Q1 is already answered (implicit Q1), keeping preamble content attached.
4. **LLM (optional)** — only consulted for genuinely ambiguous weak markers (order conflict, out-of-sequence without a numbered run) and for mapping each block to a question. Arrow markers (`1→`, `2→`) are always questions and never suppressed.
5. **Post-processing** — adjacent same-question blocks split by a weak marker are merged back; duplicate attempts (repeated strong marker) are kept as separate answer entries; unmapped blocks are deduplicated into `unmapped_content`.

## Repository layout

```text
.
├── input/                 # one OCR .txt per student (ignored by git)
├── logs/                  # run logs (ignored by git)
├── output/                # per-student JSON + debug/ (ignored by git)
├── model_answers.md       # canonical questions, stems + model answers
├── question_paper.txt     # optional exam paper context
├── src/
│   ├── main.py                 # batch entry point
│   ├── answer_processor.py     # pipeline: segmentation + mapping + review
│   ├── config.py               # Config dataclass, env override, defaults
│   ├── model_answers.py        # loads model_answers.md
│   ├── question_paper.py       # parses question_paper.txt
│   ├── preprocess.py           # normalization + OCR artifact stripping
│   ├── validation.py           # result coercion/validation helpers
│   ├── models.py               # Candidate/AnswerBlock/ProcessingResult
│   ├── logger.py, exceptions.py, utils.py
│   └── llm/
│       ├── client.py           # local HF transformers client (chat template, retries, cache)
│       ├── prompt.py           # question-mapping prompt (strict JSON schema)
│       ├── prompts.py          # boundary-adjudication prompt
│       ├── schemas.py          # LLM JSON parsing + bool/numeric coercion
│       └── mapper.py           # per-block question mapping
├── tests/                # pytest suite (deterministic; no model download)
├── requirements.txt
├── .env.example          # every supported environment variable
└── README.md
```

> Legacy modules kept for compatibility/tests: `src/segment.py`, `src/regex_patterns.py` (alternative deterministic-only segmenter), `src/parser.py`, `src/llm/evaluator.py`. The production path is `main.py → answer_processor.py`.

## Install

```bash
git clone <this-repo>
cd Segmentation-main
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
```

On NVIDIA GPU install the CUDA-compatible PyTorch wheel **first** (see https://pytorch.org/get-started/locally/), then install the rest. On CPU-only machines set `LLM_4BIT=false` and `LLM_DEVICE=auto` (the pipeline still works deterministically; the LLM runs in fp32 and is slower).

The first LLM-enabled run downloads the model from the Hugging Face Hub (a few GB, cached locally). For rate-limited or the latest repos set `HF_TOKEN` (optional).

## Quick start

```powershell
# 1. Put one OCR text file per student in input/ (e.g. student_1.txt)
# 2. Make sure model_answers.md matches your paper
# 3. Run the batch:

$env:LLM_ENABLED = "true"        # enables Granite (4-bit, temperature 0)
py -m src.main
```

Linux/macOS: `LLM_ENABLED=true py -m src.main`

Results: `output/student_1.json` (minimal) and `output/debug/student_1_debug.json` (audit + review + normalized text).

Run the test suite (no model needed):

```bash
py -m pytest
```

## Input format

One OCR `.txt` per student; markers may be explicit or numbered:

```text
Q1 A data structure is a specialized way of organizing data...
1. Primitive data structure
2. Non-primitive data structure
Q2 An algorithm is a finite sequence...
Q3 Complexity analysis measures time and space...
Q4 Explain Array and Linked List...
=======
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
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
```

## Output format

<<<<<<< HEAD
Minimal production JSON (duplicate attempts become multiple entries with the same `question_id`):

```json
{
    "student_id": "student_1",
    "exam_id": "",
    "answers": [
        {"question_id": "Q1", "answer": "A data structure is..."},
        {"question_id": "Q2", "answer": "An algorithm is..."}
    ],
    "unmapped_content": []
}
```

Meaningful OCR that cannot be safely mapped is preserved as `{"text": ...}` objects in `unmapped_content` — never silently dropped. Full review + audit (LLM call counts, model, device, dtype, quantization, per-student durations) goes to `output/debug/`.

## Model

| Setting | Value |
|---|---|
| Default model | `ibm-granite/granite-3.3-2b-instruct` (Hugging Face) |
| Quantization | NF4 4-bit (BitsAndBytes), double quant, FP16 compute |
| Device | `cuda:0` when available, else `cpu` |
| Temperature | 0.0 (deterministic decoding) |
| Context | truncated to 4096 input tokens, 64–96 new tokens, JSON-only parser |
| Roles | (a) boundary adjudication on ambiguous weak markers; (b) question mapping with a strict `subject_match` gate |

Alternatives: set `LLM_MODEL_PATH` to any HF causal LM (e.g. `Qwen/Qwen2.5-1.5B-Instruct`). The model is loaded once per process and reused across students; a failure anywhere becomes a review item instead of a crash.

## Configuration

Everything is configurable via environment variables (copy `.env.example` → `.env`):

| Variable | Default | Meaning |
|---|---|---|
| `LLM_ENABLED` | `false` | `true` turns on the local LLM |
| `LLM_MODEL_PATH` / `LOCAL_LLM_MODEL` | `ibm-granite/granite-3.3-2b-instruct` | HF model id |
| `LLM_DEVICE` | `auto` | `auto`/`cuda`/`cpu` |
| `LLM_MAX_INPUT_TOKENS` | `4096` | context truncation |
| `LLM_MAX_NEW_TOKENS` | `64` | generation cap (mapping uses min 96) |
| `LLM_TEMPERATURE` | `0.0` | sampling temp (0 = greedy) |
| `LLM_4BIT` / `LLM_4BIT_COMPUTE_DTYPE` | `true` / `float16` | 4-bit load toggle |
| `QUESTION_CONFIDENCE_THRESHOLD` | `0.85` | minimum confidence to auto-accept |
| `HUMAN_REVIEW_THRESHOLD` | `0.60` | under this → explicit review |
| `MAX_LLM_CONTEXT` | `3000` | surrounding-context characters |
| `MAX_LLM_CALLS_PER_DOCUMENT` | `64` | per-student LLM budget |
| `MAX_SEGMENTATION_LLM_CALLS_PER_DOCUMENT` | `32` | segmentation-only budget |
| `CACHE_ENABLED` | `true` | in-memory prompt cache |
| `EXAM_ID` | `""` | identifier written to every JSON |
=======
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
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5

## Testing

```bash
py -m pytest
```

<<<<<<< HEAD
47 tests cover: strong/weak marker handling, internal numbered lists, consecutive-run suppression, out-of-order markers, duplicate attempts, non-sequential question labels, OCR artifacts (`<|im_…|>`, `</s>`), years/figures/pages/tables, subject-match rejection, legacy LLM vocabulary rejection, and the full student_8 flow. Tests run entirely on fakes — no model download.

## Known limitations

- Input must be UTF-8 text; hidden/empty files are skipped.
- A structurally ambiguous weak marker that is *not* part of a numbered run still relies on the 2B LLM's judgment.
- An unmarked document with no strong markers is deliberately treated conservatively: it is surfaced for human review rather than force-mapped (e.g. an off-topic Java answer sheet maps to `unmapped_content`, not a wrong question).
- The LLM improves ambiguous interpretation but cannot guarantee correctness; human review remains part of the workflow.

## License

No license is specified in this repository.
=======
Tests cover years, figures, pages, tables, formulas, numbered answer lists, non-sequential labels, multiline paper questions, marks, and uncertain structure.

## Known limitations

- UTF-8 input is supported.
- Hidden and empty files are skipped.
- OCR with no marker cannot be reliably mapped to a question without semantic evidence; it is reviewed rather than guessed.
- Wrong student markers require stronger question-answer compatibility evidence than this lightweight implementation currently provides.
- A local LLM improves ambiguous interpretation but cannot guarantee correctness. Human review remains part of the workflow.
>>>>>>> f8cc56e38cf02ef6b68a67167c29c9c818a54aa5
