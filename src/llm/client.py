from __future__ import annotations

import hashlib
import logging
from typing import Any

from src.llm.prompt import mapping_prompt
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
        self.logger = logger or logging.getLogger(__name__)
        self._tokenizer: Any = None
        self._model: Any = None
        self._device: str | None = None
        self._cache: dict[str, StructuredLLMResult] = {}

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
            raise RuntimeError("Local LLM requires torch and transformers. Install requirements.txt.") from error
        self._device = "cuda" if self.device_setting == "auto" and torch.cuda.is_available() else ("cpu" if self.device_setting == "auto" else self.device_setting)
        self.logger.info("Loading local LLM %s on %s", self.model_path, self._device)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_path)
        self._model.to(self._device)
        self._model.eval()
        self.logger.info("Local LLM ready: %s (%s)", self.model_path, self._device)

    def analyze_structure(self, context: dict[str, object]) -> StructuredLLMResult:
        if not self.enabled:
            return StructuredLLMResult("ambiguous", None, 0.0, "Local LLM is disabled.", True)
        prompt = mapping_prompt(context)
        key = hashlib.sha256(prompt.encode()).hexdigest()
        if self.cache_enabled and key in self._cache:
            return self._cache[key]
        try:
            self._load()
            inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.max_input_tokens).to(self._device)
            import torch
            with torch.inference_mode():
                output = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=self.temperature > 0, temperature=max(self.temperature, 0.01), pad_token_id=self._tokenizer.eos_token_id)
            generated = output[0][inputs["input_ids"].shape[1]:]
            result = parse_llm_json(self._tokenizer.decode(generated, skip_special_tokens=True))
        except Exception as error:
            result = StructuredLLMResult("ambiguous", None, 0.0, f"Local LLM failure: {error}", True)
        if self.cache_enabled:
            self._cache[key] = result
        return result

    def close(self) -> None:
        self._model = None
        self._tokenizer = None
