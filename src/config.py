from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    project_dir: Path
    input_dir: Path
    output_dir: Path
    logs_dir: Path
    encoding: str = "utf-8"
    llm_enabled: bool = False
    llm_model: str = "ibm-granite/granite-3.3-2b-instruct"
    llm_base_url: str = "http://127.0.0.1:11434/api/generate"
    question_confidence_threshold: float = 0.85
    human_review_threshold: float = 0.60
    max_llm_context: int = 3000
    max_llm_calls_per_document: int = 64
    max_segmentation_llm_calls_per_document: int = 32
    cache_enabled: bool = True
    model_path: str = "ibm-granite/granite-3.3-2b-instruct"
    device: str = "auto"
    max_input_tokens: int = 4096
    max_new_tokens: int = 64
    temperature: float = 0.0
    model_answers_path: Path | None = None
    exam_id: str = ""
    quantization_4bit: bool = True
    quantization_compute_dtype: str = "float16"

    @classmethod
    def from_project_root(cls, project_root: str | Path) -> "Config":
        root = Path(project_root)

        return cls(
            project_dir=root,
            input_dir=root / "input",
            output_dir=root / "output",
            logs_dir=root / "logs",
            llm_enabled=False,
            model_answers_path=root / "model_answers.md",
        )

    @classmethod
    def from_environment(cls, project_root: str | Path) -> "Config":
        base = cls.from_project_root(project_root)

        return cls(
            **{
                **base.__dict__,
                "llm_enabled": os.getenv(
                    "LLM_ENABLED",
                    "true",
                ).lower() in {"1", "true", "yes"},
                "llm_model": os.getenv(
                    "LLM_MODEL",
                    base.llm_model,
                ),
                "llm_base_url": os.getenv(
                    "LLM_BASE_URL",
                    base.llm_base_url,
                ),
                "question_confidence_threshold": float(
                    os.getenv(
                        "QUESTION_CONFIDENCE_THRESHOLD",
                        base.question_confidence_threshold,
                    )
                ),
                "human_review_threshold": float(
                    os.getenv(
                        "HUMAN_REVIEW_THRESHOLD",
                        base.human_review_threshold,
                    )
                ),
                "max_llm_context": int(
                    os.getenv(
                        "MAX_LLM_CONTEXT",
                        base.max_llm_context,
                    )
                ),
                "max_llm_calls_per_document": int(
                    os.getenv(
                        "MAX_LLM_CALLS_PER_DOCUMENT",
                        base.max_llm_calls_per_document,
                    )
                ),
                "max_segmentation_llm_calls_per_document": int(
                    os.getenv(
                        "MAX_SEGMENTATION_LLM_CALLS_PER_DOCUMENT",
                        base.max_segmentation_llm_calls_per_document,
                    )
                ),
                "cache_enabled": os.getenv(
                    "CACHE_ENABLED",
                    "true",
                ).lower() in {"1", "true", "yes"},
                "model_path": os.getenv(
                    "LLM_MODEL_PATH",
                    os.getenv("LOCAL_LLM_MODEL", base.model_path),
                ),
                "device": os.getenv(
                    "LLM_DEVICE",
                    base.device,
                ),
                "max_input_tokens": int(
                    os.getenv(
                        "LLM_MAX_INPUT_TOKENS",
                        base.max_input_tokens,
                    )
                ),
                "max_new_tokens": int(
                    os.getenv(
                        "LLM_MAX_NEW_TOKENS",
                        base.max_new_tokens,
                    )
                ),
                "temperature": float(
                    os.getenv(
                        "LLM_TEMPERATURE",
                        base.temperature,
                    )
                ),
                "exam_id": os.getenv("EXAM_ID", base.exam_id),
                "quantization_4bit": os.getenv(
                    "LLM_4BIT",
                    "true",
                ).lower() in {"1", "true", "yes"},
                "quantization_compute_dtype": os.getenv(
                    "LLM_4BIT_COMPUTE_DTYPE",
                    base.quantization_compute_dtype,
                ),
            }
        )


DEFAULT_CONFIG = Config.from_environment(
    Path(__file__).resolve().parent.parent
)
