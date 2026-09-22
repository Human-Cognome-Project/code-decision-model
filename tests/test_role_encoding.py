import torch
from torch import nn

from cdm import CodeDecisionModel, HashTextEncoder
from cdm.synthetic import DecisionExample
from cdm.training import preencode_examples


class RoleAwareEncoder(nn.Module):
    def __init__(self, dim=4):
        super().__init__()
        self.dim = dim
        self.anchor = nn.Parameter(torch.zeros(1), requires_grad=False)
        self.calls = []

    def encode_role(self, texts, *, role):
        texts = list(texts)
        self.calls.append((role, tuple(texts)))
        offsets = {
            "context": 1.0,
            "question": 2.0,
            "candidate": 3.0,
        }
        rows = []
        for text in texts:
            rows.append(
                torch.tensor(
                    [offsets[role], float(len(text)), 0.0, 1.0],
                    device=self.anchor.device,
                )
            )
        return torch.stack(rows)

    def forward(self, texts):
        raise AssertionError("role-aware path should use encode_role")


def test_model_passes_semantic_roles_to_encoder():
    encoder = RoleAwareEncoder()
    model = CodeDecisionModel(encoder=encoder, dim=4, hidden=8)

    dc = model.encode_context("same", "same")
    candidates = model.encode_candidates(["same", "other"])

    assert dc.context[0].item() == 1.0
    assert dc.question[0].item() == 2.0
    assert candidates[0, 0].item() == 3.0
    assert [call[0] for call in encoder.calls] == [
        "context",
        "question",
        "candidate",
    ]


def test_preencoding_caches_identical_text_separately_by_role():
    encoder = RoleAwareEncoder()
    model = CodeDecisionModel(encoder=encoder, dim=4, hidden=8)
    example = DecisionExample(
        context="same",
        question="same",
        candidates=("same", "other"),
        answer_index=0,
        task="test",
        source="repo::x.py",
    )

    encoded = preencode_examples(model, [example], batch_size=16)[0]

    assert encoded.decision_context.context[0].item() == 1.0
    assert encoded.decision_context.question[0].item() == 2.0
    assert encoded.candidate_embeddings[0, 0].item() == 3.0

    role_calls = {role: texts for role, texts in encoder.calls}
    assert role_calls["context"] == ("same",)
    assert role_calls["question"] == ("same",)
    assert role_calls["candidate"] == ("same", "other")


def test_legacy_encoder_still_uses_forward_path():
    torch.manual_seed(7)
    encoder = HashTextEncoder(dim=8, buckets=128)
    model = CodeDecisionModel(encoder=encoder, dim=8, hidden=12)

    logits = model(
        "def f(x): return x",
        "Which candidate is f?",
        ["f", "g"],
    )

    assert logits.shape == (2,)


def test_invalid_encoder_role_is_rejected():
    encoder = RoleAwareEncoder()
    model = CodeDecisionModel(encoder=encoder, dim=4, hidden=8)

    try:
        model.encode_texts(["x"], role="unknown")
    except ValueError as exc:
        assert "unsupported encoder role" in str(exc)
    else:
        raise AssertionError("expected role validation")
