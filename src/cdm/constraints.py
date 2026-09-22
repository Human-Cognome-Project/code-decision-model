"""Hard environmental constraints for post-score decision filtering.

Unique priors belong outside the neural model as machine-checkable constraints.
This module provides a minimal interface so deterministic validators can veto or
filter candidates after the discriminative scorer has produced logits.

The neural scores remain untouched; constraints only decide which candidates are
still legal and how the final distribution is formed from the surviving set.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import torch
from torch.nn import functional as F


@dataclass(frozen=True)
class ConstraintResult:
    """Outcome of applying one or more constraints to a candidate set.

    Attributes
    ----------
    allowed:
        Boolean mask, one entry per candidate. True means the candidate survives.
    reasons:
        Optional human-readable explanation for each rejected candidate
        (empty string when allowed).
    """

    allowed: tuple[bool, ...]
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.reasons and len(self.reasons) != len(self.allowed):
            raise ValueError("reasons length must match allowed length")


class Constraint(Protocol):
    """Deterministic check over a decision instance.

    Implementations must be deterministic for the supplied decision and any
    machine-checkable state captured by the constraint object. They may consume
    precomputed facts from parsers, type checkers, tests, or other deterministic
    tools, but must not consult the neural model or any external LLM.
    """

    def check(
        self,
        code_context: str,
        question: str,
        candidates: Sequence[str],
    ) -> ConstraintResult:
        ...


@dataclass(frozen=True)
class ConstrainedDecision:
    """Final decision after neural scoring and hard constraint application.

    If every candidate is rejected the decision is marked ``escalate`` so the
    surrounding system can fall back to a human or a broader search.
    """

    scores: torch.Tensor
    probabilities: torch.Tensor
    allowed: tuple[bool, ...]
    chosen_index: int | None
    escalate: bool
    reasons: tuple[str, ...] = ()


def apply_constraints(
    scores: torch.Tensor,
    code_context: str,
    question: str,
    candidates: Sequence[str],
    constraints: Sequence[Constraint],
) -> ConstrainedDecision:
    """Filter neural scores by hard constraints and renormalise.

    Parameters
    ----------
    scores:
        Raw logits from the decision head, shape ``(n_candidates,)``.
    constraints:
        Ordered list of deterministic checks. A candidate must pass *all* of
        them to remain allowed.

    Returns
    -------
    ConstrainedDecision
        Surviving distribution and an explicit escalate flag when nothing
        remains legal.
    """
    if scores.ndim != 1 or scores.shape[0] != len(candidates):
        raise ValueError(
            f"scores shape {tuple(scores.shape)} does not match "
            f"{len(candidates)} candidates"
        )

    n = len(candidates)
    allowed = [True] * n
    reasons = [""] * n

    for constraint in constraints:
        result = constraint.check(code_context, question, candidates)
        if len(result.allowed) != n:
            raise ValueError("constraint returned wrong number of decisions")
        for i, ok in enumerate(result.allowed):
            if not ok and allowed[i]:
                allowed[i] = False
                if result.reasons:
                    reasons[i] = result.reasons[i]
                else:
                    reasons[i] = type(constraint).__name__

    allowed_t = tuple(allowed)
    reasons_t = tuple(reasons)

    if not any(allowed_t):
        # Nothing legal — escalate rather than force a choice.
        return ConstrainedDecision(
            scores=scores.detach(),
            probabilities=torch.zeros_like(scores),
            allowed=allowed_t,
            chosen_index=None,
            escalate=True,
            reasons=reasons_t,
        )

    # Mask illegal candidates to -inf so softmax concentrates on the survivors.
    masked = scores.clone()
    for i, ok in enumerate(allowed_t):
        if not ok:
            masked[i] = -float("inf")

    probs = F.softmax(masked, dim=-1)
    chosen = int(torch.argmax(probs).item())

    return ConstrainedDecision(
        scores=scores.detach(),
        probabilities=probs.detach(),
        allowed=allowed_t,
        chosen_index=chosen,
        escalate=False,
        reasons=reasons_t,
    )


# ---------------------------------------------------------------------------
# Minimal built-in constraints (examples / test fixtures)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequireSubstring:
    """Reject candidates that do not contain a required literal substring.

    Useful for simple structural filters (e.g. must mention a particular
    symbol or decorator) without involving the neural model.
    """

    needle: str
    case_sensitive: bool = True

    def check(
        self,
        code_context: str,
        question: str,
        candidates: Sequence[str],
    ) -> ConstraintResult:
        needle = self.needle if self.case_sensitive else self.needle.lower()
        allowed = []
        reasons = []
        for c in candidates:
            text = c if self.case_sensitive else c.lower()
            ok = needle in text
            allowed.append(ok)
            reasons.append("" if ok else f"missing required substring {self.needle!r}")
        return ConstraintResult(allowed=tuple(allowed), reasons=tuple(reasons))


@dataclass(frozen=True)
class RejectSubstring:
    """Reject candidates that contain a forbidden literal substring."""

    needle: str
    case_sensitive: bool = True

    def check(
        self,
        code_context: str,
        question: str,
        candidates: Sequence[str],
    ) -> ConstraintResult:
        needle = self.needle if self.case_sensitive else self.needle.lower()
        allowed = []
        reasons = []
        for c in candidates:
            text = c if self.case_sensitive else c.lower()
            ok = needle not in text
            allowed.append(ok)
            reasons.append("" if ok else f"contains forbidden substring {self.needle!r}")
        return ConstraintResult(allowed=tuple(allowed), reasons=tuple(reasons))


@dataclass(frozen=True)
class AllAllowed:
    """No-op constraint; every candidate survives. Useful as a baseline."""

    def check(
        self,
        code_context: str,
        question: str,
        candidates: Sequence[str],
    ) -> ConstraintResult:
        return ConstraintResult(allowed=tuple(True for _ in candidates))
