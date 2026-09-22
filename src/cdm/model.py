"""Dynamic candidate decision model.

The important architectural constraint is that repository context, question, and
candidate answers are encoded independently. Candidate count therefore does not
consume a shared prompt token budget, and repository/candidate representations can
be cached.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import torch
from torch import nn


@dataclass(frozen=True)
class EncodedDecisionContext:
    """Reusable representation of a code context and question."""

    context: torch.Tensor
    question: torch.Tensor


class CodeDecisionModel(nn.Module):
    """Score arbitrary runtime-defined candidates against code context and a question."""

    def __init__(self, encoder: nn.Module, dim: int, hidden: int = 256) -> None:
        super().__init__()
        self.encoder = encoder
        self.dim = dim
        # Pairwise features make the scorer sensitive to both alignment and mismatch.
        feature_dim = dim * 7
        self.scorer = nn.Sequential(
            nn.LayerNorm(feature_dim),
            nn.Linear(feature_dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, 1),
        )

    def encode_texts(
        self,
        texts: Sequence[str],
        *,
        role: str,
    ) -> torch.Tensor:
        """Encode texts with an optional semantic role understood by the backbone.

        Legacy encoders keep working through the ordinary forward path. Retrieval-style
        encoders can expose encode_role(texts, role=...) to distinguish query/context
        representations from candidate-code representations.
        """
        if role not in {"context", "question", "candidate"}:
            raise ValueError(f"unsupported encoder role: {role}")
        role_encoder = getattr(self.encoder, "encode_role", None)
        if role_encoder is None:
            enc = self.encoder(texts)
        else:
            enc = role_encoder(texts, role=role)
        if enc.ndim != 2 or enc.shape != (len(texts), self.dim):
            raise ValueError(
                f"encoder returned {tuple(enc.shape)}, expected "
                f"({len(texts)}, {self.dim}) for role {role}"
            )
        return enc

    def encode_context(self, code_context: str, question: str) -> EncodedDecisionContext:
        context = self.encode_texts([code_context], role="context")[0]
        q = self.encode_texts([question], role="question")[0]
        return EncodedDecisionContext(context=context, question=q)

    def encode_candidates(self, candidates: Sequence[str]) -> torch.Tensor:
        if not candidates:
            raise ValueError("at least one candidate is required")
        return self.encode_texts(candidates, role="candidate")

    def score_encoded(
        self,
        decision_context: EncodedDecisionContext,
        candidate_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        c = decision_context.context.expand(candidate_embeddings.shape[0], -1)
        q = decision_context.question.expand(candidate_embeddings.shape[0], -1)
        a = candidate_embeddings
        features = torch.cat(
            [
                c,
                q,
                a,
                c * a,
                q * a,
                torch.abs(c - a),
                torch.abs(q - a),
            ],
            dim=-1,
        )
        return self.scorer(features).squeeze(-1)

    def forward(self, code_context: str, question: str, candidates: Sequence[str]) -> torch.Tensor:
        dc = self.encode_context(code_context, question)
        ce = self.encode_candidates(candidates)
        return self.score_encoded(dc, ce)

    def probabilities(self, code_context: str, question: str, candidates: Sequence[str]) -> torch.Tensor:
        return torch.softmax(self.forward(code_context, question, candidates), dim=-1)
