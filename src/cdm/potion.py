"""Static code embedding adapter for potion-code-16M-v2."""
from __future__ import annotations

from collections.abc import Iterable

import torch
from torch import nn


class PotionCodeEncoder(nn.Module):
    """Frozen Model2Vec adapter for minishlab/potion-code-16M-v2.

    The model is a static code embedding table rather than a transformer. Query and
    candidate roles use the same published encoding path, so encode_role exists only
    to satisfy the role-aware encoder contract.
    """

    def __init__(
        self,
        model_name: str = "minishlab/potion-code-16M-v2",
        *,
        max_length: int | None = 8192,
        normalize_embeddings: bool | None = None,
        model=None,
        frozen: bool = True,
    ) -> None:
        super().__init__()
        if not frozen:
            raise ValueError("PotionCodeEncoder is a frozen static encoder")
        if max_length is not None and max_length < 1:
            raise ValueError("max_length must be positive or None")

        if model is None:
            try:
                from model2vec import StaticModel
            except ImportError as exc:
                raise ImportError(
                    "PotionCodeEncoder requires the optional potion dependencies. "
                    "Install with: pip install -e '.[potion]'"
                ) from exc

            kwargs = {}
            if normalize_embeddings is not None:
                kwargs["normalize"] = normalize_embeddings
            model = StaticModel.from_pretrained(
                model_name,
                force_download=False,
                **kwargs,
            )
        else:
            if normalize_embeddings is not None and hasattr(model, "normalize"):
                model.normalize = normalize_embeddings

        self.model = model
        self.max_length = max_length
        self.frozen = True

        dimension = getattr(model, "dim", None)
        if dimension is None:
            raise ValueError("static model must expose a dim attribute")
        self.dim = int(dimension)

    def encode_many(self, texts: Iterable[str]) -> torch.Tensor:
        materialized = list(texts)
        if not materialized:
            return torch.empty((0, self.dim), dtype=torch.float32)

        # Model2Vec 0.9 exposes max_length on encode(), while newer main also
        # supports a model-level default. Passing it per call works across both.
        encoded = self.model.encode(materialized, max_length=self.max_length)
        tensor = torch.as_tensor(encoded, dtype=torch.float32)
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)
        if tensor.ndim != 2 or tensor.shape != (len(materialized), self.dim):
            raise ValueError(
                f"Potion model returned {tuple(tensor.shape)}, expected "
                f"({len(materialized)}, {self.dim})"
            )
        return tensor

    def encode_role(self, texts: Iterable[str], *, role: str) -> torch.Tensor:
        if role not in {"context", "question", "candidate"}:
            raise ValueError(f"unsupported Potion role: {role}")
        return self.encode_many(texts)

    def forward(self, texts: Iterable[str]) -> torch.Tensor:
        return self.encode_many(texts)
