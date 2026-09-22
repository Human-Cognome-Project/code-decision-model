import torch

from cdm import CodeDecisionModel, HashTextEncoder


def make_model():
    torch.manual_seed(7)
    encoder = HashTextEncoder(dim=32, buckets=1024)
    return CodeDecisionModel(encoder=encoder, dim=32, hidden=48)


def test_dynamic_candidate_count():
    model = make_model()
    logits = model("def f(): return 1", "Which symbol is defined?", ["f", "g", "h"])
    assert logits.shape == (3,)
    assert torch.isclose(model.probabilities(
        "def f(): return 1", "Which symbol is defined?", ["f", "g", "h"]
    ).sum(), torch.tensor(1.0), atol=1e-6)


def test_candidate_permutation_equivariance():
    model = make_model().eval()
    context = "def parse_header(data): return data[0]"
    question = "Which function parses the header?"
    a = ["parse_header", "read_packet", "dispatch"]
    b = ["dispatch", "parse_header", "read_packet"]

    la = model(context, question, a)
    lb = model(context, question, b)

    assert torch.allclose(la, lb[torch.tensor([1, 2, 0])], atol=1e-6)


def test_cached_encoding_matches_direct_scoring():
    model = make_model().eval()
    context = "int add(int a, int b) { return a + b; }"
    question = "Which candidate performs addition?"
    candidates = ["add", "subtract"]

    direct = model(context, question, candidates)
    dc = model.encode_context(context, question)
    ce = model.encode_candidates(candidates)
    cached = model.score_encoded(dc, ce)

    assert torch.allclose(direct, cached, atol=1e-6)
