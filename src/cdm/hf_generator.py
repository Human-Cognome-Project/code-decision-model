"""Hugging Face causal-LM adapter for corrective-turn repair experiments.

Import-guarded: default CI does not download weights. Unit tests inject tokenizer
and model fakes; real runs use the optional hf extra.
"""
from __future__ import annotations

from typing import Any

from .generators import GeneratorFactory, RepairGenerator


DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
DEFAULT_REVISION = "ea3f2471cf1b1f0db85067f1ef93848e38e88c25"
DEFAULT_SYSTEM_PROMPT = (
    "You are a precise code repair engine. Return only the complete repaired "
    "Python function. Do not explain the answer."
)


class HFCausalRepairGenerator:
    """Map a repair prompt to generated text via a causal language model.

    Decoding parameters are fixed at construction. Tokenizer/model objects may be
    injected so paired arms can use fresh generator wrappers while sharing the
    same immutable loaded weights.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        revision: str | None = DEFAULT_REVISION,
        max_new_tokens: int = 512,
        temperature: float = 0.0,
        top_p: float = 1.0,
        seed: int | None = 0,
        device: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        use_chat_template: bool = True,
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

            if tokenizer is None:
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    revision=revision,
                )
            if model is None:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    revision=revision,
                    torch_dtype=torch.float32,
                )
                if device is None:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                model = model.to(device)
                model.eval()

        if getattr(tokenizer, "pad_token_id", None) is None:
            eos = getattr(tokenizer, "eos_token", None)
            if eos is not None:
                tokenizer.pad_token = eos

        self.tokenizer = tokenizer
        self.model = model
        self.model_name = model_name
        self.revision = revision
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.seed = seed
        self.system_prompt = system_prompt
        self.use_chat_template = use_chat_template
        self._device = device

    def _render_prompt(self, prompt: str) -> str:
        if self.use_chat_template and hasattr(self.tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
            try:
                return self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            except (TypeError, ValueError):
                pass

        if self.system_prompt:
            return self.system_prompt + "\n\n" + prompt
        return prompt

    def __call__(self, prompt: str) -> str:
        import torch

        if self.seed is not None:
            torch.manual_seed(self.seed)

        rendered = self._render_prompt(prompt)
        inputs = self.tokenizer(rendered, return_tensors="pt")
        if self._device is not None:
            inputs = {
                key: value.to(self._device)
                for key, value in inputs.items()
            }
        elif hasattr(self.model, "device"):
            inputs = {
                key: value.to(self.model.device)
                for key, value in inputs.items()
            }

        do_sample = self.temperature > 0
        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        eos_token_id = getattr(self.tokenizer, "eos_token_id", None)
        if eos_token_id is not None:
            generate_kwargs["eos_token_id"] = eos_token_id
        if do_sample:
            generate_kwargs["temperature"] = self.temperature
            generate_kwargs["top_p"] = self.top_p

        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, **generate_kwargs)

        prompt_len = inputs["input_ids"].shape[-1]
        continuation = output_ids[0, prompt_len:]
        return self.tokenizer.decode(
            continuation,
            skip_special_tokens=True,
        ).strip()


def make_hf_generator_factory(
    model_name: str = DEFAULT_MODEL,
    *,
    revision: str | None = DEFAULT_REVISION,
    **kwargs: Any,
) -> GeneratorFactory:
    """Return fresh wrappers that lazily share one loaded model/tokenizer.

    The E021 paired harness asks for a fresh generator per arm to avoid mutable
    trajectory leakage. Reloading immutable weights for each arm is unnecessary,
    so the factory caches only tokenizer/model resources.
    """

    shared: dict[str, Any] = {}

    def factory() -> RepairGenerator:
        if "tokenizer" in kwargs or "model" in kwargs:
            return HFCausalRepairGenerator(
                model_name,
                revision=revision,
                **kwargs,
            )

        if not shared:
            generator = HFCausalRepairGenerator(
                model_name,
                revision=revision,
                **kwargs,
            )
            shared["tokenizer"] = generator.tokenizer
            shared["model"] = generator.model
            return generator

        return HFCausalRepairGenerator(
            model_name,
            revision=revision,
            tokenizer=shared["tokenizer"],
            model=shared["model"],
            **kwargs,
        )

    return factory
