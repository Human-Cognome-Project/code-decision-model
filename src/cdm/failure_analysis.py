"""E028 failure-conditioned analysis for structured selection outcomes.

This module is analysis-only: it does not alter prompts, scoring, generation,
verification, or the frozen E027 protocol. It turns already-recorded paired
selection outcomes into machine-counted failure mechanisms.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .structured_edit import PairedSelectionOutcome
from .synthetic import DecisionExample


@dataclass(frozen=True)
class AssistedFailureSignature:
    recommendation_correct: bool
    assisted_success: bool
    first_attempt_reason: str
    terminal_reason: str
    followed_recommendation: bool | None
    ignored_correct_recommendation: bool
    followed_wrong_recommendation: bool
    feedback_recovery_failed: bool


@dataclass(frozen=True)
class FailureSummary:
    tasks: int
    assisted_failures: int
    wrong_recommendations: int
    correct_recommendations_ignored: int
    wrong_recommendations_followed: int
    feedback_recovery_failures: int
    unparseable_first_attempts: int
    terminal_unparseable: int

    @property
    def assisted_failure_rate(self) -> float:
        return self.assisted_failures / self.tasks


def failure_signature(
    example: DecisionExample,
    outcome: PairedSelectionOutcome,
    recommendation_index: int,
) -> AssistedFailureSignature:
    """Describe how the assisted arm behaved relative to its recommendation."""
    if not 0 <= recommendation_index < len(example.candidates):
        raise ValueError("recommendation_index out of range")
    if not outcome.assisted.attempts:
        raise ValueError("assisted outcome must contain at least one attempt")

    attempts = outcome.assisted.attempts
    first = attempts[0].verification
    terminal = attempts[-1].verification
    recommendation_correct = recommendation_index == example.answer_index

    if first.selected_index is None:
        followed: bool | None = None
    else:
        followed = first.selected_index == recommendation_index

    return AssistedFailureSignature(
        recommendation_correct=recommendation_correct,
        assisted_success=outcome.assisted.success,
        first_attempt_reason=first.reason,
        terminal_reason=terminal.reason,
        followed_recommendation=followed,
        ignored_correct_recommendation=(
            recommendation_correct
            and not outcome.assisted.success
            and followed is not True
        ),
        followed_wrong_recommendation=(
            not recommendation_correct
            and not outcome.assisted.success
            and followed is True
        ),
        feedback_recovery_failed=(
            not outcome.assisted.success and len(attempts) > 1
        ),
    )


def summarize_failures(
    examples: Sequence[DecisionExample],
    outcomes: Sequence[PairedSelectionOutcome],
    recommendation_indices: Sequence[int],
) -> FailureSummary:
    """Aggregate E027-style assisted failure mechanisms."""
    if not examples:
        raise ValueError("at least one example is required")
    if not (len(examples) == len(outcomes) == len(recommendation_indices)):
        raise ValueError("examples, outcomes, and recommendation_indices must have equal length")

    signatures = [
        failure_signature(example, outcome, recommendation)
        for example, outcome, recommendation in zip(
            examples, outcomes, recommendation_indices
        )
    ]
    failures = [signature for signature in signatures if not signature.assisted_success]

    return FailureSummary(
        tasks=len(signatures),
        assisted_failures=len(failures),
        wrong_recommendations=sum(not s.recommendation_correct for s in signatures),
        correct_recommendations_ignored=sum(
            s.ignored_correct_recommendation for s in signatures
        ),
        wrong_recommendations_followed=sum(
            s.followed_wrong_recommendation for s in signatures
        ),
        feedback_recovery_failures=sum(
            s.feedback_recovery_failed for s in signatures
        ),
        unparseable_first_attempts=sum(
            s.first_attempt_reason == "unparseable_selection" for s in failures
        ),
        terminal_unparseable=sum(
            s.terminal_reason == "unparseable_selection" for s in failures
        ),
    )


def summarize_failures_by(
    examples: Sequence[DecisionExample],
    outcomes: Sequence[PairedSelectionOutcome],
    recommendation_indices: Sequence[int],
    key: Callable[[DecisionExample], str],
) -> dict[str, FailureSummary]:
    """Group failure summaries, e.g. by repository or task family."""
    if not (len(examples) == len(outcomes) == len(recommendation_indices)):
        raise ValueError("examples, outcomes, and recommendation_indices must have equal length")

    grouped: dict[str, tuple[list[DecisionExample], list[PairedSelectionOutcome], list[int]]] = {}
    for example, outcome, recommendation in zip(
        examples, outcomes, recommendation_indices
    ):
        name = key(example)
        if name not in grouped:
            grouped[name] = ([], [], [])
        grouped[name][0].append(example)
        grouped[name][1].append(outcome)
        grouped[name][2].append(recommendation)

    return {
        name: summarize_failures(*grouped[name])
        for name in sorted(grouped)
    }


def render_failure_report(summary: FailureSummary) -> str:
    """Render a compact, deterministic failure-mechanism report."""
    return "\n".join([
        f"tasks: {summary.tasks}",
        f"assisted terminal failures: {summary.assisted_failures} "
        f"({100 * summary.assisted_failure_rate:.1f}%)",
        f"wrong recommendations: {summary.wrong_recommendations}",
        f"correct recommendations ignored on terminal failures: "
        f"{summary.correct_recommendations_ignored}",
        f"wrong recommendations followed on terminal failures: "
        f"{summary.wrong_recommendations_followed}",
        f"failed to recover after deterministic feedback: "
        f"{summary.feedback_recovery_failures}",
        f"terminal failures unparseable on first attempt: "
        f"{summary.unparseable_first_attempts}",
        f"terminal failures ending unparseable: {summary.terminal_unparseable}",
    ])
