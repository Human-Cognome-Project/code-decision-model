import torch

from cdm import CodeDecisionModel, HashTextEncoder
from cdm.synthetic import python_direct_call_examples
from cdm.training import (
    accuracy_encoded,
    fit_encoded,
    preencode_examples,
)


SOURCE = """
def normalize(x):
    return x.strip()

def parse(x):
    return int(x)

def clamp(x):
    return max(0, x)

def stage_one(x):
    return normalize(x)

def stage_two(x):
    return parse(x)

def stage_three(x):
    return clamp(x)
"""


class CountingHashEncoder(HashTextEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.batches = []

    def forward(self, texts):
        texts = list(texts)
        self.batches.append(tuple(texts))
        return super().forward(texts)


def _frozen_model():
    torch.manual_seed(17)
    encoder = CountingHashEncoder(dim=32, buckets=2048)
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    encoder.eval()
    return CodeDecisionModel(encoder=encoder, dim=32, hidden=48)


def test_preencoded_logits_match_direct_logits():
    model = _frozen_model().eval()
    examples = python_direct_call_examples(SOURCE)

    direct = [
        model(example.context, example.question, example.candidates).detach()
        for example in examples
    ]
    encoded = preencode_examples(model, examples, batch_size=128)

    cached = [
        model.score_encoded(item.decision_context, item.candidate_embeddings).detach()
        for item in encoded
    ]

    for a, b in zip(direct, cached):
        assert torch.allclose(a, b, atol=1e-6)


def test_preencoding_deduplicates_shared_texts():
    model = _frozen_model().eval()
    examples = python_direct_call_examples(SOURCE)

    model.encoder.batches.clear()
    preencode_examples(model, examples, batch_size=128)

    flattened = [text for batch in model.encoder.batches for text in batch]
    assert len(flattened) == len(set(flattened))

    shared_candidate = examples[0].candidates[0]
    assert sum(text == shared_candidate for text in flattened) == 1


def test_cached_training_never_reinvokes_encoder_and_can_fit():
    model = _frozen_model()
    examples = python_direct_call_examples(SOURCE)
    encoded = preencode_examples(model, examples, batch_size=128)

    calls_after_encoding = len(model.encoder.batches)
    history = fit_encoded(model, encoded, epochs=100)

    assert len(model.encoder.batches) == calls_after_encoding
    assert history[-1] < history[0] * 0.1
    assert accuracy_encoded(model, encoded) == 1.0


def test_preencoding_rejects_trainable_encoder():
    torch.manual_seed(3)
    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=16, buckets=256),
        dim=16,
        hidden=24,
    )
    examples = python_direct_call_examples(SOURCE)

    try:
        preencode_examples(model, examples)
    except ValueError as exc:
        assert "frozen encoder" in str(exc)
    else:
        raise AssertionError("expected frozen-encoder guard")
