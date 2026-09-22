import torch

from cdm import (
    CodeDecisionModel,
    CosineMixScorer,
    HashTextEncoder,
    PairwiseMLPScorer,
)
from cdm.model import EncodedDecisionContext


def test_default_model_uses_pairwise_mlp_scorer():
    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=8, buckets=128),
        dim=8,
        hidden=12,
    )
    assert isinstance(model.scorer, PairwiseMLPScorer)


def test_cosine_mix_has_only_two_trainable_scalars():
    scorer = CosineMixScorer()
    params = [p for p in scorer.parameters() if p.requires_grad]

    assert len(params) == 2
    assert sum(p.numel() for p in params) == 2
    assert torch.isclose(scorer.context_weight, torch.tensor(0.5))
    assert torch.isclose(scorer.scale, torch.tensor(1.0))


def test_cosine_mix_initially_averages_context_and_question_cosines():
    scorer = CosineMixScorer()
    context = torch.tensor([1.0, 0.0])
    question = torch.tensor([0.0, 1.0])
    candidates = torch.tensor([
        [1.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
    ])

    scores = scorer(context, question, candidates)

    expected = torch.tensor([
        0.5,
        0.5,
        2 ** -0.5,
    ])
    assert torch.allclose(scores, expected, atol=1e-6)


def test_injected_cosine_scorer_preserves_candidate_permutation_equivariance():
    torch.manual_seed(7)
    encoder = HashTextEncoder(dim=16, buckets=256)
    model = CodeDecisionModel(
        encoder=encoder,
        dim=16,
        scorer=CosineMixScorer(),
    ).eval()

    context = "def parse_packet(data): return parse_header(data)"
    question = "Which candidate parses the header?"
    a = ["parse_header", "decode_payload", "dispatch"]
    b = ["dispatch", "parse_header", "decode_payload"]

    la = model(context, question, a)
    lb = model(context, question, b)

    assert torch.allclose(la, lb[torch.tensor([1, 2, 0])], atol=1e-6)


def test_cosine_scorer_scale_changes_softmax_sharpness_not_ranking():
    scorer = CosineMixScorer()
    dc = EncodedDecisionContext(
        context=torch.tensor([1.0, 0.0]),
        question=torch.tensor([1.0, 0.0]),
    )
    candidates = torch.tensor([
        [1.0, 0.0],
        [0.8, 0.2],
        [0.0, 1.0],
    ])
    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=2, buckets=32),
        dim=2,
        scorer=scorer,
    )

    low = torch.softmax(model.score_encoded(dc, candidates), dim=-1)
    scorer.log_scale.data.fill_(2.0)
    high = torch.softmax(model.score_encoded(dc, candidates), dim=-1)

    assert int(low.argmax()) == int(high.argmax()) == 0
    assert high.max() > low.max()
