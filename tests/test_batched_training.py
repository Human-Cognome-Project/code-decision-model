import torch

from cdm import (
    CodeDecisionModel,
    CosineMixScorer,
    HashTextEncoder,
    PairwiseMLPScorer,
)
from cdm.model import EncodedDecisionContext
from cdm.synthetic import python_direct_call_examples
from cdm.training import (
    EncodedDecisionExample,
    accuracy_encoded_batched,
    collate_encoded_examples,
    encoded_batch_loss,
    encoded_example_loss,
    fit_encoded_batched,
    preencode_examples,
)


def test_batched_scorers_match_stacked_single_decisions():
    torch.manual_seed(5)
    contexts = torch.randn(3, 8)
    questions = torch.randn(3, 8)
    candidates = torch.randn(3, 4, 8)

    for scorer in (PairwiseMLPScorer(8, hidden=12), CosineMixScorer()):
        batched = scorer(contexts, questions, candidates)
        single = torch.stack(
            [
                scorer(contexts[i], questions[i], candidates[i])
                for i in range(3)
            ],
            dim=0,
        )
        assert batched.shape == (3, 4)
        assert torch.allclose(batched, single, atol=1e-6)


def _encoded_example(dim, candidate_count, answer, seed):
    generator = torch.Generator().manual_seed(seed)
    return EncodedDecisionExample(
        decision_context=EncodedDecisionContext(
            context=torch.randn(dim, generator=generator),
            question=torch.randn(dim, generator=generator),
        ),
        candidate_embeddings=torch.randn(
            candidate_count,
            dim,
            generator=generator,
        ),
        answer_index=answer,
        task="test",
        source=f"f{seed}.py",
    )


def test_batched_loss_matches_mean_individual_loss():
    torch.manual_seed(9)
    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=8, buckets=64),
        dim=8,
        hidden=10,
    )
    examples = [
        _encoded_example(8, 4, 0, 1),
        _encoded_example(8, 4, 2, 2),
        _encoded_example(8, 4, 3, 3),
    ]

    expected = torch.stack(
        [encoded_example_loss(model, example) for example in examples]
    ).mean()
    batch = collate_encoded_examples(examples)
    actual = encoded_batch_loss(model, batch)

    assert torch.allclose(actual, expected, atol=1e-6)


def test_collation_rejects_mixed_candidate_counts():
    examples = [
        _encoded_example(8, 2, 0, 1),
        _encoded_example(8, 3, 1, 2),
    ]

    try:
        collate_encoded_examples(examples)
    except ValueError as exc:
        assert "candidate count" in str(exc)
    else:
        raise AssertionError("expected mixed-cardinality validation")


def test_batched_fit_handles_mixed_candidate_counts_without_padding():
    torch.manual_seed(12)
    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=8, buckets=64),
        dim=8,
        hidden=10,
    )
    examples = [
        _encoded_example(8, 2, 0, 1),
        _encoded_example(8, 2, 1, 2),
        _encoded_example(8, 3, 1, 3),
        _encoded_example(8, 3, 2, 4),
    ]

    history = fit_encoded_batched(
        model,
        examples,
        epochs=3,
        batch_size=4,
        lr=1e-2,
        seed=7,
    )

    assert len(history) == 3
    assert all(torch.isfinite(torch.tensor(history)))
    score = accuracy_encoded_batched(model, examples, batch_size=4)
    assert 0.0 <= score <= 1.0


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
        self.calls = 0

    def forward(self, texts):
        self.calls += 1
        return super().forward(texts)


def test_batched_cached_training_can_fit_without_reinvoking_encoder():
    torch.manual_seed(17)
    encoder = CountingHashEncoder(dim=32, buckets=2048)
    for parameter in encoder.parameters():
        parameter.requires_grad_(False)
    encoder.eval()

    model = CodeDecisionModel(
        encoder=encoder,
        dim=32,
        hidden=48,
    )
    examples = python_direct_call_examples(SOURCE)
    encoded = preencode_examples(model, examples, batch_size=128)
    calls_after_encoding = encoder.calls

    history = fit_encoded_batched(
        model,
        encoded,
        epochs=140,
        batch_size=3,
        lr=2e-2,
        seed=11,
    )

    assert encoder.calls == calls_after_encoding
    assert history[-1] < history[0] * 0.1
    assert accuracy_encoded_batched(model, encoded, batch_size=3) == 1.0
