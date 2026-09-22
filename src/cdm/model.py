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

    def encode_context(self, code_context: str, question: str) -> EncodedDecisionContext:
        enc = self.encoder([code_context, question])
        if enc.shape != (2, self.dim):
            raise ValueError(f"encoder returned {tuple(enc.shape)}, expected (2, {self.dim})")
        return EncodedDecisionContext(context=enc[0], question=enc[1])

    def encode_candidates(self, candidates: Sequence[str]) -> torch.Tensor:
        if not candidates:
            raise ValueError("at least one candidate is required")
        enc = self.encoder(candidates)
        if enc.ndim != 2 or enc.shape[1] != self.dim:
            raise ValueError(f"encoder returned invalid candidate shape {tuple(enc.shape)}")
        return enc

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
