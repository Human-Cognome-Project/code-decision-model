"""Hugging Face causal-LM adapter for the E021/E022 repair harness.

Import-guarded: default CI does not download weights. Inject tokenizer and
model for unit tests. Real runs use the optional ``hf`` extra.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .generators import GeneratorFactory, RepairGenerator


class HFCausalRepairGenerator:
    """Map a repair prompt to generated text via a causal language model.

    Satisfies ``RepairGenerator``. Decoding parameters are fixed at construction
    so paired baseline/assisted arms share the same generator behaviour.
    """

    def __init__(
        self,
        model_name: str = "Salesforce/codegen-350M-mono",
        *,
        max_new_tokens: int = 256,
        temperature: float = 0.0,
        top_p: float = 1.0,
        seed: int | None = 0,
        device: str | None = None,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be positive")
        if temperature < 0:
            raise ValueError("temperature must be non-negative")

        if tokenizer is None or model is None:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError as exc:
                raise ImportError(
                    "HFCausalRepairGenerator requires the optional 'hf' "
                    "dependencies. Install with: pip install -e '.[hf]'"
                ) from exc

            tokenizer = tokenizer or AutoTokenizer.from_pretrained(model_name)
            if model is None:
                model = AutoModelForCausalLM.from_pretrained(model_name)
                if device is None:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                model = model.to(device)
                model.eval()

        if getattr(tokenizer, "pad_token_id", None) is None:
            # Many causal code models only expose eos; reuse it for padding.
            eos = getattr(tokenizer, "eos_token", None)
            if eos is not None:
                tokenizer.pad_token = eos

        self.tokenizer = tokenizer
        self.model = model
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.seed = seed
        self._device = device

    def __call__(self, prompt: str) -> str:
        import torch

        if self.seed is not None:
            torch.manual_seed(self.seed)

        inputs = self.tokenizer(prompt, return_tensors="pt")
        if self._device is not None:
            inputs = {key: value.to(self._device) for key, value in inputs.items()}
        elif hasattr(self.model, "device"):
            inputs = {key: value.to(self.model.device) for key, value in inputs.items()}

        do_sample = self.temperature > 0
        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        if do_sample:
            generate_kwargs["temperature"] = self.temperature
            generate_kwargs["top_p"] = self.top_p

        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **generate_kwargs)

        # Decode only the continuation after the prompt.
        prompt_len = inputs["input_ids"].shape[-1]
        continuation = output_ids[0, prompt_len:]
        return self.tokenizer.decode(continuation, skip_special_tokens=True)


def make_hf_generator_factory(
    model_name: str = "Salesforce/codegen-350M-mono",
    **kwargs: Any,
) -> GeneratorFactory:
    """Return a factory that builds a fresh HFCausalRepairGenerator per arm."""

    def factory() -> RepairGenerator:
        return HFCausalRepairGenerator(model_name, **kwargs)

    return factory
