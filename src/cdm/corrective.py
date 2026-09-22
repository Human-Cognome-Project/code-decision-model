"""Paired corrective-turn statistics for E021/E023-style experiments (E026).

Both the full-function repair harness (E021) and the structured-edit harness
(E023) produce paired baseline/assisted outcomes per task. This module turns a
collection of those pairs into the report the project's success criterion asks
for, with uncertainty that respects source-file clustering (E012) and exact
paired tests that remain valid at pilot sample sizes.

Nothing here fabricates a correction-turn delta: it is defined only when both
arms resolve the task, exactly as the harnesses define it. Attempt counts within
budget are reported separately as a censored burden measure.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from .synthetic import DecisionExample


class _ArmOutcome(Protocol):
    success: bool

    @property
    def attempts_used(self) -> int: ...

    @property
    def correction_turns(self) -> int: ...

    @property
    def first_pass_success(self) -> bool: ...


class PairedOutcome(Protocol):
    """Structural type shared by PairedRepairOutcome and PairedSelectionOutcome."""

    baseline: _ArmOutcome
    assisted: _ArmOutcome


@dataclass(frozen=True)
class ArmSummary:
    tasks: int
    first_pass_successes: int
    successes: int
    total_attempts: int

    @property
    def terminal_failures(self) -> int:
        return self.tasks - self.successes

    @property
    def first_pass_rate(self) -> float:
        return self.first_pass_successes / self.tasks

    @property
    def success_rate(self) -> float:
        return self.successes / self.tasks

    @property
    def mean_attempts(self) -> float:
        return self.total_attempts / self.tasks


@dataclass(frozen=True)
class PairedCorrectiveSummary:
    tasks: int
    baseline: ArmSummary
    assisted: ArmSummary
    both_succeed: int
    assisted_only: int
    baseline_only: int
    neither: int
    correction_turn_deltas: tuple[int, ...]
    """Baseline minus assisted corrections, one entry per paired success."""

    @property
    def success_rate_delta(self) -> float:
        return self.assisted.success_rate - self.baseline.success_rate

    @property
    def mean_attempts_delta(self) -> float:
        """Baseline minus assisted attempts within budget, over all tasks."""
        return self.baseline.mean_attempts - self.assisted.mean_attempts

    @property
    def mean_correction_turn_delta(self) -> float | None:
        if not self.correction_turn_deltas:
            return None
        return sum(self.correction_turn_deltas) / len(self.correction_turn_deltas)

    @property
    def assisted_fewer(self) -> int:
        return sum(delta > 0 for delta in self.correction_turn_deltas)

    @property
    def assisted_same(self) -> int:
        return sum(delta == 0 for delta in self.correction_turn_deltas)

    @property
    def assisted_more(self) -> int:
        return sum(delta < 0 for delta in self.correction_turn_deltas)


def _arm_summary(arms: Sequence[_ArmOutcome]) -> ArmSummary:
    return ArmSummary(
        tasks=len(arms),
        first_pass_successes=sum(arm.first_pass_success for arm in arms),
        successes=sum(arm.success for arm in arms),
        total_attempts=sum(arm.attempts_used for arm in arms),
    )


def summarize_paired(outcomes: Sequence[PairedOutcome]) -> PairedCorrectiveSummary:
    """Aggregate paired outcomes into the standard corrective-turn report."""
    if not outcomes:
        raise ValueError("at least one paired outcome is required")

    both = assisted_only = baseline_only = neither = 0
    deltas: list[int] = []
    for outcome in outcomes:
        b, a = outcome.baseline.success, outcome.assisted.success
        if b and a:
            both += 1
            deltas.append(
                outcome.baseline.correction_turns - outcome.assisted.correction_turns
            )
        elif a:
            assisted_only += 1
        elif b:
            baseline_only += 1
        else:
            neither += 1

    return PairedCorrectiveSummary(
        tasks=len(outcomes),
        baseline=_arm_summary([o.baseline for o in outcomes]),
        assisted=_arm_summary([o.assisted for o in outcomes]),
        both_succeed=both,
        assisted_only=assisted_only,
        baseline_only=baseline_only,
        neither=neither,
        correction_turn_deltas=tuple(deltas),
    )


def by_task(example: DecisionExample) -> str:
    return example.task


def by_namespace(example: DecisionExample) -> str:
    """Repository namespace from sources of the form namespace::path."""
    if example.source is None or "::" not in example.source:
        raise ValueError("namespace grouping requires namespaced source provenance")
    return example.source.split("::", 1)[0]


def summarize_paired_by(
    examples: Sequence[DecisionExample],
    outcomes: Sequence[PairedOutcome],
    key: Callable[[DecisionExample], str],
) -> dict[str, PairedCorrectiveSummary]:
    """Per-group summaries, e.g. by repository or function-vs-method task."""
    _validate(examples, outcomes)
    groups: dict[str, list[PairedOutcome]] = {}
    for example, outcome in zip(examples, outcomes):
        groups.setdefault(key(example), []).append(outcome)
    return {name: summarize_paired(groups[name]) for name in sorted(groups)}


# ---------------------------------------------------------------------------
# Exact paired tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExactTest:
    """Two-sided exact binomial test at p = 1/2 on discordant observations."""

    favourable: int
    unfavourable: int
    ties: int
    p_value: float

    @property
    def discordant(self) -> int:
        return self.favourable + self.unfavourable


def _two_sided_binomial(k: int, n: int) -> float:
    """Exact two-sided p-value for k successes of n at p = 1/2."""
    if n == 0:
        return 1.0
    low = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(low + 1)) / 2**n
    return min(1.0, 2.0 * tail)


def exact_mcnemar(summary: PairedCorrectiveSummary) -> ExactTest:
    """Exact McNemar test on tasks resolved by exactly one arm."""
    return ExactTest(
        favourable=summary.assisted_only,
        unfavourable=summary.baseline_only,
        ties=summary.both_succeed + summary.neither,
        p_value=_two_sided_binomial(
            summary.assisted_only,
            summary.assisted_only + summary.baseline_only,
        ),
    )


def exact_sign_test(summary: PairedCorrectiveSummary) -> ExactTest:
    """Exact sign test on correction-turn deltas over paired successes."""
    fewer, more = summary.assisted_fewer, summary.assisted_more
    return ExactTest(
        favourable=fewer,
        unfavourable=more,
        ties=summary.assisted_same,
        p_value=_two_sided_binomial(fewer, fewer + more),
    )


def discordant_pairs_for_significance(
    favourable_ratio: float,
    *,
    alpha: float = 0.05,
    limit: int = 10_000,
) -> int:
    """Smallest discordant count at which an exact test rejects at ``alpha``.

    ``favourable_ratio`` is the assumed share of discordant pairs that favour
    the assisted arm (e.g. 0.8 for a 4:1 split). Counts are rounded to the
    nearest integer per size, so the result is a planning aid, not a promise.
    """
    if not 0.5 < favourable_ratio <= 1.0:
        raise ValueError("favourable_ratio must be in (0.5, 1]")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")
    for n in range(1, limit + 1):
        k = round(favourable_ratio * n)
        if _two_sided_binomial(k, n) < alpha:
            return n
    raise ValueError("no discordant count within limit reaches significance")


# ---------------------------------------------------------------------------
# Source-clustered bootstrap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairedInterval:
    statistic: str
    estimate: float
    lower: float
    upper: float
    samples: int
    confidence: float


_STATISTICS = ("success_rate_delta", "mean_attempts_delta", "mean_correction_turn_delta")


def _validate(
    examples: Sequence[DecisionExample],
    outcomes: Sequence[PairedOutcome],
) -> None:
    if not examples:
        raise ValueError("at least one example is required")
    if len(examples) != len(outcomes):
        raise ValueError("examples and outcomes must have equal length")
    if any(example.source is None for example in examples):
        raise ValueError("clustered statistics require source provenance")


def _statistic(summary: PairedCorrectiveSummary, name: str) -> float | None:
    return getattr(summary, name)


def _percentile(sorted_values: list[float], q: float) -> float:
    if q <= 0.0:
        return sorted_values[0]
    if q >= 1.0:
        return sorted_values[-1]
    position = q * (len(sorted_values) - 1)
    lo = int(position)
    hi = min(lo + 1, len(sorted_values) - 1)
    weight = position - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def cluster_bootstrap_paired(
    examples: Sequence[DecisionExample],
    outcomes: Sequence[PairedOutcome],
    *,
    statistic: str = "success_rate_delta",
    bootstrap_samples: int = 5000,
    confidence: float = 0.95,
    seed: int = 0,
    strata: Callable[[DecisionExample], str] | None = None,
) -> PairedInterval:
    """Percentile bootstrap over source files for one paired statistic.

    Tasks from one source file share a caller pool and style, so files are the
    resampling unit, as in E012. The paired structure is preserved because each
    task carries both arms. When ``strata`` is provided, source files are sampled
    independently within each stratum so its number of source-file draws is held
    fixed. E025 used ``strata=by_namespace`` to preserve repository composition.

    ``mean_correction_turn_delta`` is conditional on paired successes; resamples
    with none are skipped and ``samples`` reports how many were kept.
    """
    _validate(examples, outcomes)
    if statistic not in _STATISTICS:
        raise ValueError(f"statistic must be one of {_STATISTICS}")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    point = _statistic(summarize_paired(outcomes), statistic)
    if point is None:
        raise ValueError("statistic is undefined: no task was resolved by both arms")

    groups: dict[str, dict[str, list[PairedOutcome]]] = {}
    for example, outcome in zip(examples, outcomes):
        stratum = strata(example) if strata is not None else "__all__"
        groups.setdefault(stratum, {}).setdefault(example.source, []).append(outcome)

    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(bootstrap_samples):
        resampled: list[PairedOutcome] = []
        for stratum in sorted(groups):
            source_groups = groups[stratum]
            keys = sorted(source_groups)
            for _ in range(len(keys)):
                key = keys[rng.randrange(len(keys))]
                resampled.extend(source_groups[key])
        value = _statistic(summarize_paired(resampled), statistic)
        if value is not None:
            values.append(value)

    if not values:
        raise ValueError("every bootstrap resample left the statistic undefined")
    values.sort()
    alpha = (1.0 - confidence) / 2.0
    return PairedInterval(
        statistic=statistic,
        estimate=point,
        lower=_percentile(values, alpha),
        upper=_percentile(values, 1.0 - alpha),
        samples=len(values),
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_report(summary: PairedCorrectiveSummary) -> str:
    """Render the standard table used in the E022/E023 experiment notes."""
    b, a = summary.baseline, summary.assisted
    lines = [
        "| Metric | Baseline | Assisted |",
        "| --- | ---: | ---: |",
        (
            f"| First-pass success | {b.first_pass_successes}/{b.tasks} "
            f"({100 * b.first_pass_rate:.1f}%) | {a.first_pass_successes}/{a.tasks} "
            f"({100 * a.first_pass_rate:.1f}%) |"
        ),
        (
            f"| Success within budget | {b.successes}/{b.tasks} "
            f"({100 * b.success_rate:.1f}%) | {a.successes}/{a.tasks} "
            f"({100 * a.success_rate:.1f}%) |"
        ),
        f"| Terminal failures | {b.terminal_failures}/{b.tasks} | {a.terminal_failures}/{a.tasks} |",
        f"| Mean attempts, all tasks | {b.mean_attempts:.2f} | {a.mean_attempts:.2f} |",
        "",
        "Paired outcomes:",
        "",
        f"- both succeed: {summary.both_succeed}",
        f"- assisted only: {summary.assisted_only}",
        f"- baseline only: {summary.baseline_only}",
        f"- neither succeeds: {summary.neither}",
    ]
    mean_delta = summary.mean_correction_turn_delta
    if mean_delta is None:
        lines.append("- correction-turn delta: not defined (no paired successes)")
    else:
        n = len(summary.correction_turn_deltas)
        lines.append(
            f"- among the {n} paired successes, assisted saved "
            f"{mean_delta:.2f} correction turns on average"
        )
        lines.append(
            f"- assisted used fewer corrections on {summary.assisted_fewer}/{n}, "
            f"the same on {summary.assisted_same}/{n}, and more on "
            f"{summary.assisted_more}/{n}"
        )
    mcnemar = exact_mcnemar(summary)
    sign = exact_sign_test(summary)
    lines.extend([
        "",
        "Exact paired tests:",
        "",
        (
            f"- McNemar on {mcnemar.discordant} discordant tasks "
            f"({mcnemar.favourable} assisted-only vs {mcnemar.unfavourable} "
            f"baseline-only): p = {mcnemar.p_value:.3f}"
        ),
        (
            f"- sign test on {sign.discordant} unequal paired deltas "
            f"({sign.favourable} fewer vs {sign.unfavourable} more, "
            f"{sign.ties} ties): p = {sign.p_value:.3f}"
        ),
    ])
    return "\n".join(lines)
