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
from torch.nn import functional as F


@dataclass(frozen=True)
class EncodedDecisionContext:
    """Reusable representation of a code context and question."""

    context: torch.Tensor
    question: torch.Tensor


def _broadcast_decision_inputs(
    context: torch.Tensor,
    question: torch.Tensor,
    candidates: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Broadcast one or many decision contexts across their candidate axis.

    Supported shapes:
    - single decision: context/question [D], candidates [K, D];
    - batch: context/question [B, D], candidates [B, K, D].
    """
    if candidates.ndim == 2:
        if context.ndim != 1 or question.ndim != 1:
            raise ValueError("single-decision context and question must be 1D")
        if (
            context.shape[0] != candidates.shape[1]
            or question.shape[0] != candidates.shape[1]
        ):
            raise ValueError("decision embedding dimensions must match")
        return (
            context.unsqueeze(0).expand(candidates.shape[0], -1),
            question.unsqueeze(0).expand(candidates.shape[0], -1),
            candidates,
        )

    if candidates.ndim == 3:
        batch, count, dim = candidates.shape
        if context.shape != (batch, dim) or question.shape != (batch, dim):
            raise ValueError(
                "batched context/question must have shape [batch, embedding_dim]"
            )
        return (
            context.unsqueeze(1).expand(-1, count, -1),
            question.unsqueeze(1).expand(-1, count, -1),
            candidates,
        )

    raise ValueError("candidate embeddings must be 2D or 3D")


class PairwiseMLPScorer(nn.Module):
    """Original expressive scorer over pairwise context/question/candidate features."""

    def __init__(self, dim: int, hidden: int = 256) -> None:
        super().__init__()
        feature_dim = dim * 7
        self.network = nn.Sequential(
            nn.LayerNorm(feature_dim),
            nn.Linear(feature_dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, 1),
        )

    def forward(
        self,
        context: torch.Tensor,
        question: torch.Tensor,
        candidates: torch.Tensor,
    ) -> torch.Tensor:
        c, q, a = _broadcast_decision_inputs(
            context,
            question,
            candidates,
        )
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
        return self.network(features).squeeze(-1)


class CosineMixScorer(nn.Module):
    """Two-parameter regularized scorer over frozen representation geometry.

    The scorer learns only:
    - how much to weight context-vs-candidate cosine relative to
      question-vs-candidate cosine;
    - a shared positive logit scale.

    A candidate-independent bias would cancel under softmax, so none is included.
    """

    def __init__(self) -> None:
        super().__init__()
        self.mix_logit = nn.Parameter(torch.tensor(0.0))
        self.log_scale = nn.Parameter(torch.tensor(0.0))

    def forward(
        self,
        context: torch.Tensor,
        question: torch.Tensor,
        candidates: torch.Tensor,
    ) -> torch.Tensor:
        c, q, a = _broadcast_decision_inputs(
            context,
            question,
            candidates,
        )
        context_scores = F.cosine_similarity(a, c, dim=-1)
        question_scores = F.cosine_similarity(a, q, dim=-1)
        mix = torch.sigmoid(self.mix_logit)
        scale = torch.exp(torch.clamp(self.log_scale, min=-5.0, max=5.0))
        return scale * (
            mix * context_scores
            + (1.0 - mix) * question_scores
        )

    @property
    def context_weight(self) -> torch.Tensor:
        return torch.sigmoid(self.mix_logit)

    @property
    def scale(self) -> torch.Tensor:
        return torch.exp(torch.clamp(self.log_scale, min=-5.0, max=5.0))


class CodeDecisionModel(nn.Module):
    """Score arbitrary runtime-defined candidates against code context and a question."""

    def __init__(
        self,
        encoder: nn.Module,
        dim: int,
        hidden: int = 256,
        *,
        scorer: nn.Module | None = None,
    ) -> None:
        super().__init__()
        self.encoder = encoder
        self.dim = dim
        self.scorer = scorer if scorer is not None else PairwiseMLPScorer(dim, hidden)

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
        return self.scorer(
            decision_context.context,
            decision_context.question,
            candidate_embeddings,
        )

    def score_encoded_batch(
        self,
        contexts: torch.Tensor,
        questions: torch.Tensor,
        candidate_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        """Score a batch of equal-cardinality encoded decisions."""
        return self.scorer(contexts, questions, candidate_embeddings)

    def forward(self, code_context: str, question: str, candidates: Sequence[str]) -> torch.Tensor:
        dc = self.encode_context(code_context, question)
        ce = self.encode_candidates(candidates)
        return self.score_encoded(dc, ce)

    def probabilities(self, code_context: str, question: str, candidates: Sequence[str]) -> torch.Tensor:
        return torch.softmax(self.forward(code_context, question, candidates), dim=-1)
