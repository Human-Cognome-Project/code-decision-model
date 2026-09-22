import torch

from cdm.potion import PotionCodeEncoder


class FakeStaticModel:
    def __init__(self, dim=5):
        self.dim = dim
        self.max_length = 512
        self.normalize = False
        self.calls = []

    def encode(self, texts):
        texts = list(texts)
        self.calls.append(tuple(texts))
        return [
            [float(len(text)), 1.0, 2.0, 3.0, 4.0][: self.dim]
            for text in texts
        ]


def test_potion_role_encoding_is_symmetric():
    fake = FakeStaticModel()
    encoder = PotionCodeEncoder(model=fake, max_length=1024)

    context = encoder.encode_role(["caller"], role="context")
    question = encoder.encode_role(["question"], role="question")
    candidate = encoder.encode_role(["candidate"], role="candidate")

    assert context.shape == question.shape == candidate.shape == (1, 5)
    assert fake.calls == [("caller",), ("question",), ("candidate",)]
    assert fake.max_length == 1024


def test_potion_adapter_has_no_trainable_parameters():
    encoder = PotionCodeEncoder(model=FakeStaticModel())
    assert list(encoder.parameters()) == []


def test_potion_normalization_override_is_forwarded_to_injected_model():
    fake = FakeStaticModel()
    encoder = PotionCodeEncoder(
        model=fake,
        normalize_embeddings=True,
    )
    assert fake.normalize is True
    assert encoder.frozen is True


def test_potion_empty_batch_has_expected_shape():
    encoder = PotionCodeEncoder(model=FakeStaticModel(dim=4))
    out = encoder([])
    assert out.shape == (0, 4)
    assert out.dtype == torch.float32


def test_potion_rejects_trainable_mode_bad_length_and_bad_role():
    try:
        PotionCodeEncoder(model=FakeStaticModel(), frozen=False)
    except ValueError as exc:
        assert "frozen" in str(exc)
    else:
        raise AssertionError("expected frozen-mode validation")

    try:
        PotionCodeEncoder(model=FakeStaticModel(), max_length=0)
    except ValueError as exc:
        assert "max_length" in str(exc)
    else:
        raise AssertionError("expected max-length validation")

    encoder = PotionCodeEncoder(model=FakeStaticModel())
    try:
        encoder.encode_role(["x"], role="unknown")
    except ValueError as exc:
        assert "role" in str(exc)
    else:
        raise AssertionError("expected role validation")
