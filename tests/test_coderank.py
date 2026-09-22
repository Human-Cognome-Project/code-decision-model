
import torch
from torch import nn

from cdm.coderank import CodeRankEncoder


class FakeSentenceTransformer(nn.Module):
    def __init__(self, dim=6):
        super().__init__()
        self._dim = dim
        self.anchor = nn.Parameter(torch.zeros(1))
        self.max_seq_length = 999
        self.calls = []

    def get_sentence_embedding_dimension(self):
        return self._dim

    def encode(self, texts, *, convert_to_tensor, normalize_embeddings, show_progress_bar):
        texts = list(texts)
        self.calls.append({
            'texts': tuple(texts),
            'convert_to_tensor': convert_to_tensor,
            'normalize_embeddings': normalize_embeddings,
            'show_progress_bar': show_progress_bar,
        })
        rows = []
        for text in texts:
            rows.append(torch.tensor([
                float(len(text)),
                float(text.startswith(CodeRankEncoder.QUERY_PREFIX)),
                1.0, 2.0, 3.0, 4.0,
            ]))
        out = torch.stack(rows)
        if normalize_embeddings:
            out = torch.nn.functional.normalize(out, dim=1)
        return out


def test_coderank_applies_query_prefix_only_to_query_side_roles():
    fake = FakeSentenceTransformer()
    encoder = CodeRankEncoder(model=fake, max_length=256)

    context = encoder.encode_role(['def caller(): ...'], role='context')
    question = encoder.encode_role(['Which function?'], role='question')
    candidate = encoder.encode_role(['def target(): ...'], role='candidate')

    assert context.shape == question.shape == candidate.shape == (1, 6)
    assert fake.calls[0]['texts'][0].startswith(CodeRankEncoder.QUERY_PREFIX)
    assert fake.calls[1]['texts'][0].startswith(CodeRankEncoder.QUERY_PREFIX)
    assert fake.calls[2]['texts'] == ('def target(): ...',)


def test_coderank_adapter_freezes_backbone_and_sets_context_window():
    fake = FakeSentenceTransformer()
    encoder = CodeRankEncoder(model=fake, max_length=1024)

    assert fake.max_seq_length == 1024
    assert all(not parameter.requires_grad for parameter in fake.parameters())
    assert fake.training is False


def test_coderank_forward_defaults_to_candidate_semantics():
    fake = FakeSentenceTransformer()
    encoder = CodeRankEncoder(model=fake, max_length=128)

    encoded = encoder(['def target(): return 1'])

    assert encoded.shape == (1, 6)
    assert fake.calls[-1]['texts'] == ('def target(): return 1',)


def test_coderank_normalization_is_forwarded():
    fake = FakeSentenceTransformer()
    encoder = CodeRankEncoder(model=fake, max_length=128, normalize_embeddings=True)

    result = encoder.encode_role(['query'], role='context')

    assert fake.calls[-1]['normalize_embeddings'] is True
    assert torch.allclose(result.norm(dim=1), torch.ones(1), atol=1e-6)


def test_coderank_rejects_trainable_mode_and_invalid_window():
    try:
        CodeRankEncoder(model=FakeSentenceTransformer(), frozen=False)
    except ValueError as exc:
        assert 'frozen=True' in str(exc)
    else:
        raise AssertionError('expected frozen-mode validation')

    try:
        CodeRankEncoder(model=FakeSentenceTransformer(), max_length=8193)
    except ValueError as exc:
        assert '8192' in str(exc)
    else:
        raise AssertionError('expected context-window validation')
