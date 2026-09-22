"""CodeRankEmbed adapter for role-aware code retrieval experiments."""
from __future__ import annotations

from collections.abc import Iterable

import torch
from torch import nn


class CodeRankEncoder(nn.Module):
    """Frozen adapter for nomic-ai/CodeRankEmbed.

    Query-side text receives the retrieval instruction prefix while candidate code
    is encoded as-is. The current adapter intentionally supports frozen inference
    only because SentenceTransformer.encode is an inference API.
    """

    QUERY_PREFIX = "Represent this query for searching relevant code: "

    def __init__(
        self,
        model_name: str = "nomic-ai/CodeRankEmbed",
        *,
        max_length: int = 8192,
        normalize_embeddings: bool = False,
        model=None,
        device: str | None = None,
        frozen: bool = True,
    ) -> None:
        super().__init__()
        if not frozen:
            raise ValueError("CodeRankEncoder currently supports frozen=True only")
        if max_length < 8 or max_length > 8192:
            raise ValueError("max_length must be between 8 and 8192")

        if model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "CodeRankEncoder requires the optional coderank dependencies. "
                    "Install with: pip install -e '.[coderank]'"
                ) from exc
            model = SentenceTransformer(
                model_name,
                trust_remote_code=True,
                device=device,
            )

        self.model = model
        self.max_length = max_length
        self.normalize_embeddings = normalize_embeddings
        self.frozen = True

        if hasattr(self.model, "max_seq_length"):
            self.model.max_seq_length = max_length

        dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None:
            raise ValueError("sentence-transformer model must expose an embedding dimension")
        self.dim = int(dimension)

        for parameter in self.model.parameters():
            parameter.requires_grad_(False)
        self.model.eval()

    def _prepare(self, texts: Iterable[str], *, role: str) -> list[str]:
        materialized = list(texts)
        if role in {"context", "question"}:
            return [self.QUERY_PREFIX + text for text in materialized]
        if role == "candidate":
            return materialized
        raise ValueError(f"unsupported CodeRank role: {role}")

    def encode_role(self, texts: Iterable[str], *, role: str) -> torch.Tensor:
        prepared = self._prepare(texts, role=role)
        if not prepared:
            return torch.empty((0, self.dim), dtype=torch.float32)

        self.model.eval()
        with torch.no_grad():
            encoded = self.model.encode(
                prepared,
                convert_to_tensor=True,
                normalize_embeddings=self.normalize_embeddings,
                show_progress_bar=False,
            )

        if not isinstance(encoded, torch.Tensor):
            encoded = torch.as_tensor(encoded)
        if encoded.ndim == 1:
            encoded = encoded.unsqueeze(0)
        if encoded.ndim != 2 or encoded.shape[1] != self.dim:
            raise ValueError(
                f"CodeRank model returned {tuple(encoded.shape)}, expected (*, {self.dim})"
            )
        return encoded

    def forward(self, texts: Iterable[str]) -> torch.Tensor:
        """Default to candidate/document semantics for direct adapter use."""
        return self.encode_role(texts, role="candidate")
