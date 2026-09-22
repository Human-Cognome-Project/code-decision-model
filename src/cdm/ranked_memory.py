"""E032 ranked feasible re-recommendation.

E028 showed that the frozen generator follows the decision recommendation on
every first attempt, and that every remaining assisted failure begins with a
wrong recommendation. E029 removes a verifier-rejected candidate from the next
turn and drops the recommendation that pointed to it.

E032 keeps E029's hard rejection memory and adds one thing the decision layer
already has: the scorer's full candidate ranking. At every turn the
recommendation is the highest-ranked candidate in the *feasible* set, where a
candidate is feasible when it passes every hard constraint (E019/E024) and has
not been rejected by the verifier. No new model call is made; the ranking is a
cached artefact of the scoring that already happened.

Two effects are separable in the trace:

- turn-0 gating: a hard constraint vetoes the scorer's top choice, so the first
  recommendation differs from the frozen loop's;
- post-rejection re-recommendation: after a wrong first choice, the next turn
  recommends the scorer's next feasible candidate instead of nothing.

Prompt mechanics are exactly E029's, so with no constraints and a ranking whose
top element is the frozen recommendation, the first-turn prompt equals E027's.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

import torch

from .constraints import Constraint, apply_constraints
from .rejection_memory import (
    build_rejection_memory_prompt,
    feedback_for_rejection_memory,
    verify_selection_with_memory,
)
from .structured_edit import SelectionAttempt, SelectionOutcome
from .synthetic import DecisionExample


@dataclass(frozen=True)
class RankedMemoryTrace:
    outcome: SelectionOutcome
    rejected_indices: tuple[int, ...]
    recommendations: tuple[int | None, ...]
    """Recommendation shown on each attempt; None means no feasible candidate."""
    allowed: tuple[bool, ...]
    """Static constraint mask over candidates, before any rejection."""

    @property
    def gated_at_turn_zero(self) -> bool:
        """True when a hard constraint changed the first recommendation."""
        return bool(self.recommendations) and self.recommendations[0] != self.top_ranked

    top_ranked: int = 0


def validate_ranking(ranking: Sequence[int], count: int) -> tuple[int, ...]:
    """A ranking is a permutation of candidate indices, best first."""
    frozen = tuple(ranking)
    if sorted(frozen) != list(range(count)):
        raise ValueError("ranking must be a permutation of all candidate indices")
    return frozen


def ranking_from_scores(scores: Sequence[float] | torch.Tensor) -> tuple[int, ...]:
    """Best-first candidate order from raw scorer logits (ties by index)."""
    values = [float(v) for v in scores]
    return tuple(sorted(range(len(values)), key=lambda i: (-values[i], i)))


def constraint_mask(
    example: DecisionExample,
    ranking: Sequence[int],
    constraints: Sequence[Constraint],
) -> tuple[bool, ...]:
    """Static feasibility from hard constraints, via the E019 path.

    Rank positions stand in for scores so the audited ``apply_constraints``
    routine produces the mask and the escalate signal.
    """
    count = len(example.candidates)
    order = validate_ranking(ranking, count)
    position = {index: pos for pos, index in enumerate(order)}
    pseudo_scores = torch.tensor([float(count - position[i]) for i in range(count)])
    decision = apply_constraints(
        pseudo_scores,
        example.context,
        example.question,
        example.candidates,
        constraints,
    )
    return decision.allowed


def ranked_recommendation(
    ranking: Sequence[int],
    *,
    allowed: Sequence[bool],
    rejected: Iterable[int],
) -> int | None:
    """Highest-ranked candidate that is allowed and not rejected, else None."""
    excluded = set(rejected)
    for index in ranking:
        if allowed[index] and index not in excluded:
            return index
    return None


def run_selection_loop_with_ranked_memory(
    example: DecisionExample,
    generate: Callable[[str], str],
    *,
    ranking: Sequence[int],
    constraints: Sequence[Constraint] = (),
    max_attempts: int = 3,
) -> RankedMemoryTrace:
    """E029 loop whose recommendation is re-derived from the ranking each turn."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    order = validate_ranking(ranking, len(example.candidates))
    allowed = constraint_mask(example, order, constraints)

    attempts: list[SelectionAttempt] = []
    recommendations: list[int | None] = []
    rejected: list[int] = []
    previous_output: str | None = None
    feedback: str | None = None

    for _ in range(max_attempts):
        recommendation = ranked_recommendation(
            order, allowed=allowed, rejected=rejected
        )
        recommendations.append(recommendation)
        prompt = build_rejection_memory_prompt(
            example,
            recommendation_index=recommendation,
            rejected_indices=rejected,
            previous_output=previous_output,
            feedback=feedback,
        )
        output = generate(prompt)
        verification = verify_selection_with_memory(
            example, output, rejected_indices=rejected
        )
        attempts.append(SelectionAttempt(prompt=prompt, output=output, verification=verification))
        if verification.valid:
            return RankedMemoryTrace(
                SelectionOutcome(True, tuple(attempts)),
                tuple(rejected),
                tuple(recommendations),
                allowed,
                top_ranked=order[0],
            )

        if (
            verification.reason == "wrong_selection"
            and verification.selected_index is not None
            and verification.selected_index not in rejected
            and len(rejected) < len(example.candidates) - 1
        ):
            rejected.append(verification.selected_index)

        previous_output = output
        feedback = feedback_for_rejection_memory(verification)

    return RankedMemoryTrace(
        SelectionOutcome(False, tuple(attempts)),
        tuple(rejected),
        tuple(recommendations),
        allowed,
        top_ranked=order[0],
    )
