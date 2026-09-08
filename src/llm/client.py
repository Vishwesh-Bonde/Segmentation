from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from src.llm.prompt import mapping_prompt
from src.llm.prompts import structure_prompt
from src.llm.schemas import parse_llm_json
from src.models import StructuredLLMResult


class LocalLLMClient:
    def __init__(self, config: Any, logger: logging.Logger | None = None) -> None:
        self.enabled = config.llm_enabled
        self.model_path = config.model_path
        self.device_setting = config.device
        self.max_input_tokens = config.max_input_tokens
        self.max_new_tokens = config.max_new_tokens
        self.temperature = config.temperature
        self.cache_enabled = config.cache_enabled
        self.quantization_4bit = config.quantization_4bit
        self.quantization_compute_dtype = config.quantization_compute_dtype
        self.logger = logger or logging.getLogger(__name__)
        self._tokenizer: Any = None
        self._model: Any = None
        self._device: str | None = None
        self._cache: dict[str, StructuredLLMResult] = {}
        self.total_duration_ms = 0
        self.quantization_mode = "none"
        self.model_dtype: str | None = None

    @property
    def device(self) -> str | None:
        return self._device

    def _load(self) -> None:
        if self._model is not None:
            return

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "Local LLM requires torch and transformers. "
                "Install requirements.txt."
            ) from error

        # Select device
        if self.device_setting == "auto":
            self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self._device = "cuda:0" if self.device_setting == "cuda" else self.device_setting

        self.logger.info(
            "Loading local LLM %s on requested device=%s",
            self.model_path,
            self._device,
        )

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)

        if self.quantization_4bit:
            if not self._device.startswith("cuda"):
                raise RuntimeError(
                    "4-bit local model loading requires CUDA. "
                    "Set LLM_4BIT=false only when a non-quantized fallback is intended."
                )
            try:
                from transformers import BitsAndBytesConfig
            except ImportError as error:
                raise RuntimeError(
                    "4-bit loading requires transformers BitsAndBytesConfig and bitsandbytes. "
                    "Install requirements.txt."
                ) from error

            compute_dtype = getattr(torch, self.quantization_compute_dtype)
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=compute_dtype,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                quantization_config=quantization_config,
                device_map={"": self._device},
                dtype=compute_dtype,
            )
            self.quantization_mode = "bitsandbytes_nf4_4bit"
            self.model_dtype = str(compute_dtype)
        else:
            dtype = torch.float16 if self._device.startswith("cuda") else torch.float32
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                dtype=dtype,
            )
            self._model.to(self._device)
            self.model_dtype = str(dtype)

        self._model.eval()

        # Verify actual model placement
        actual_device = next(self._model.parameters()).device

        self.logger.info(
            "Local LLM ready: model=%s requested_device=%s actual_device=%s dtype=%s quantization=%s",
            self.model_path,
            self._device,
            actual_device,
            self.model_dtype,
            self.quantization_mode,
        )

    def analyze_structure(
        self,
        context: dict[str, object],
    ) -> StructuredLLMResult:

        if not self.enabled:
            return StructuredLLMResult(
                "ambiguous",
                None,
                0.0,
                "Local LLM is disabled.",
                True,
            )

        prompt = mapping_prompt(context) if context.get("operation") == "mapping" else structure_prompt(context)

        key = hashlib.sha256(
            prompt.encode()
        ).hexdigest()

        if self.cache_enabled and key in self._cache:
            return self._cache[key]

        start = time.perf_counter()

        self.logger.info(
            "LLM_CALL_START model=%s device=%s quantization=%s",
            self.model_path,
            self._device or self.device_setting,
            self.quantization_mode,
        )

        try:
            self._load()

            if hasattr(self._tokenizer, "apply_chat_template"):
                chat_prompt = self._tokenizer.apply_chat_template(
                    [
                        {
                            "role": "system",
                            "content": "You return only the requested JSON object. Do not explain your reasoning outside the JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                )
                inputs = self._tokenizer(
                    chat_prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.max_input_tokens,
                )
            else:
                inputs = self._tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.max_input_tokens,
                )
            inputs = inputs.to(self._device)

            import torch

            budget = (
                max(self.max_new_tokens, 96)
                if context.get("operation") == "mapping"
                else self.max_new_tokens
            )
            generation_kwargs = {
                "max_new_tokens": budget,
                "do_sample": self.temperature > 0,
                "pad_token_id": self._tokenizer.eos_token_id,
            }

            if self.temperature > 0:
                generation_kwargs["temperature"] = (
                    self.temperature
                )

            with torch.inference_mode():
                output = self._model.generate(
                    **inputs,
                    **generation_kwargs,
                )

            generated = output[0][
                inputs["input_ids"].shape[1]:
            ]

            decoded = self._tokenizer.decode(
                generated,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )
            try:
                result = parse_llm_json(decoded)
            except ValueError:
                retry_tokens = min(max(self.max_new_tokens * 2, 192), 256)
                self.logger.warning(
                    "Retrying truncated/invalid structured output with max_new_tokens=%s",
                    retry_tokens,
                )
                retry_output = self._model.generate(
                    **inputs,
                    max_new_tokens=retry_tokens,
                    do_sample=False,
                    pad_token_id=self._tokenizer.eos_token_id,
                )
                retry_generated = retry_output[0][inputs["input_ids"].shape[1]:]
                retry_decoded = self._tokenizer.decode(
                    retry_generated,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )
                result = parse_llm_json(retry_decoded)

        except Exception as error:
            result = StructuredLLMResult(
                "ambiguous",
                None,
                0.0,
                f"Local LLM failure: {error}",
                True,
            )
            self.logger.exception(
                "LLM_CALL_FAILURE model=%s device=%s: %s",
                self.model_path,
                self.device or self.device_setting,
                error,
            )

        finally:
            duration_ms = int(
                (time.perf_counter() - start) * 1000
            )

            self.total_duration_ms += duration_ms

            self.logger.info(
                "LLM_CALL_END model=%s device=%s duration_ms=%s",
                self.model_path,
                self.device or self.device_setting,
                duration_ms,
            )

        if self.cache_enabled:
            self._cache[key] = result

        return result

    def close(self) -> None:
        self._model = None
        self._tokenizer = None