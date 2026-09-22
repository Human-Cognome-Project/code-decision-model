"""Unit tests for HFCausalRepairGenerator without network downloads."""
from __future__ import annotations

import torch
from torch import nn

from cdm.hf_generator import (
    DEFAULT_MODEL,
    DEFAULT_REVISION,
    HFCausalRepairGenerator,
    make_hf_generator_factory,
)


class FakeTokenizer:
    pad_token_id = 0
    eos_token_id = 2
    eos_token = "</s>"
    pad_token = None

    def __init__(self):
        self.seen_texts = []

    def __call__(self, text, return_tensors="pt"):
        self.seen_texts.append(text)
        ids = [hash(tok) % 50 + 1 for tok in text.split()] or [1]
        return {
            "input_ids": torch.tensor([ids], dtype=torch.long),
            "attention_mask": torch.ones(1, len(ids), dtype=torch.long),
        }

    def decode(self, ids, skip_special_tokens=True):
        return "def repaired():\n    return normalize(value)\n"


class FakeChatTokenizer(FakeTokenizer):
    def apply_chat_template(
        self,
        messages,
        tokenize=False,
        add_generation_prompt=True,
    ):
        assert tokenize is False
        assert add_generation_prompt is True
        return (
            "SYSTEM:" + messages[0]["content"]
            + "\nUSER:" + messages[1]["content"]
            + "\nASSISTANT:"
        )


class FakeCausalModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.device = torch.device("cpu")
        self.param = nn.Parameter(torch.zeros(1))
        self.last_kwargs = None

    def generate(self, input_ids, attention_mask=None, max_new_tokens=8, **kwargs):
        self.last_kwargs = kwargs
        batch, _ = input_ids.shape
        cont = torch.ones(batch, max_new_tokens, dtype=torch.long)
        return torch.cat([input_ids, cont], dim=-1)


def test_hf_generator_decodes_continuation_only():
    tokenizer = FakeTokenizer()
    model = FakeCausalModel()
    gen = HFCausalRepairGenerator(
        tokenizer=tokenizer,
        model=model,
        max_new_tokens=4,
        temperature=0.0,
        seed=0,
    )
    out = gen("Repair the caller")
    assert "def repaired" in out
    assert "normalize" in out
    assert model.last_kwargs["do_sample"] is False
    assert model.last_kwargs["eos_token_id"] == tokenizer.eos_token_id


def test_chat_template_and_system_instruction_are_used():
    tokenizer = FakeChatTokenizer()
    gen = HFCausalRepairGenerator(
        tokenizer=tokenizer,
        model=FakeCausalModel(),
        max_new_tokens=4,
    )
    gen("Repair the caller")
    rendered = tokenizer.seen_texts[-1]
    assert "SYSTEM:You are a precise code repair engine." in rendered
    assert "USER:Repair the caller" in rendered
    assert "ASSISTANT:" in rendered


def test_hf_generator_rejects_invalid_limits():
    try:
        HFCausalRepairGenerator(
            tokenizer=FakeTokenizer(),
            model=FakeCausalModel(),
            max_new_tokens=0,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_factory_builds_fresh_wrappers_sharing_injected_resources():
    tokenizer = FakeTokenizer()
    model = FakeCausalModel()
    factory = make_hf_generator_factory(
        tokenizer=tokenizer,
        model=model,
        max_new_tokens=4,
    )
    first = factory()
    second = factory()
    assert first is not second
    assert first.model is model
    assert second.model is model
    assert first.tokenizer is tokenizer
    assert second.tokenizer is tokenizer


def test_default_model_and_revision_match_live_e022():
    assert DEFAULT_MODEL == "Qwen/Qwen2.5-Coder-0.5B-Instruct"
    assert DEFAULT_REVISION == "ea3f2471cf1b1f0db85067f1ef93848e38e88c25"
