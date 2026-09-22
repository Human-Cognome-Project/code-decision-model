from types import SimpleNamespace

import torch
from torch import nn

from cdm.unixcoder import UniXcoderEncoder


class FakeTokenizer:
    cls_token = "<s>"
    sep_token = "</s>"
    pad_token_id = 1

    def __init__(self):
        self.vocab = {
            "<s>": 0,
            "<pad>": 1,
            "</s>": 2,
            "<encoder-only>": 3,
        }

    def tokenize(self, text):
        return text.split()

    def convert_tokens_to_ids(self, tokens):
        out = []
        for token in tokens:
            if token not in self.vocab:
                self.vocab[token] = len(self.vocab)
            out.append(self.vocab[token])
        return out


class FakeModel(nn.Module):
    def __init__(self, dim=8):
        super().__init__()
        self.config = SimpleNamespace(hidden_size=dim, pad_token_id=1)
        self.embedding = nn.Embedding(128, dim)
        self.last_input_ids = None
        self.last_attention_mask = None

    def forward(self, input_ids, attention_mask):
        self.last_input_ids = input_ids.detach().clone()
        self.last_attention_mask = attention_mask.detach().clone()
        return SimpleNamespace(last_hidden_state=self.embedding(input_ids))


def test_unixcoder_adapter_uses_encoder_mode_prefix_and_bidirectional_mask():
    tokenizer = FakeTokenizer()
    backbone = FakeModel()
    encoder = UniXcoderEncoder(tokenizer=tokenizer, model=backbone, max_length=16)

    encoded = encoder(["alpha beta", "gamma"])

    assert encoded.shape == (2, 8)
    assert backbone.last_input_ids[0, :3].tolist() == [0, 3, 2]
    assert backbone.last_attention_mask.ndim == 3
    valid_len = 6
    assert backbone.last_attention_mask[0, :valid_len, :valid_len].all()


def test_frozen_unixcoder_adapter_disables_backbone_gradients():
    backbone = FakeModel()
    encoder = UniXcoderEncoder(
        tokenizer=FakeTokenizer(),
        model=backbone,
        frozen=True,
    )

    assert all(not p.requires_grad for p in backbone.parameters())
    out = encoder(["def f(): return 1"])
    assert not out.requires_grad


def test_unixcoder_adapter_rejects_invalid_context_window():
    try:
        UniXcoderEncoder(
            tokenizer=FakeTokenizer(),
            model=FakeModel(),
            max_length=1024,
        )
    except ValueError as exc:
        assert "max_length" in str(exc)
    else:
        raise AssertionError("expected max_length validation")
