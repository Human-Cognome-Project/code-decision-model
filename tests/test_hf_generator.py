"""Unit tests for HFCausalRepairGenerator without network downloads."""
from __future__ import annotations

import torch
from torch import nn

from cdm.hf_generator import HFCausalRepairGenerator


class FakeTokenizer:
    pad_token_id = 0
    eos_token = "</s>"
    pad_token = None

    def __call__(self, text, return_tensors="pt"):
        # One token per whitespace-separated piece; deterministic ids.
        ids = [hash(tok) % 50 + 1 for tok in text.split()] or [1]
        return {
            "input_ids": torch.tensor([ids], dtype=torch.long),
            "attention_mask": torch.ones(1, len(ids), dtype=torch.long),
        }

    def decode(self, ids, skip_special_tokens=True):
        if hasattr(ids, "tolist"):
            ids = ids.tolist()
        return "def repaired():\n    return normalize(value)\n"


class FakeCausalModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.device = torch.device("cpu")
        self.param = nn.Parameter(torch.zeros(1))

    def generate(self, input_ids, attention_mask=None, max_new_tokens=8, **kwargs):
        batch, prompt_len = input_ids.shape
        # Append a fixed continuation of max_new_tokens ones.
        cont = torch.ones(batch, max_new_tokens, dtype=torch.long)
        return torch.cat([input_ids, cont], dim=-1)


def test_hf_generator_decodes_continuation_only():
    gen = HFCausalRepairGenerator(
        tokenizer=FakeTokenizer(),
        model=FakeCausalModel(),
        max_new_tokens=4,
        temperature=0.0,
        seed=0,
    )
    out = gen("Repair the caller")
    assert "def repaired" in out
    assert "normalize" in out


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


def test_factory_builds_callable():
    from cdm.hf_generator import make_hf_generator_factory

    factory = make_hf_generator_factory(
        tokenizer=FakeTokenizer(),
        model=FakeCausalModel(),
        max_new_tokens=4,
    )
    gen = factory()
    assert callable(gen)
    assert "repaired" in gen("prompt")
