"""Tests for paired corrective-turn statistics (E025)."""
from __future__ import annotations

import pytest

from cdm.corrective import (
    by_namespace,
    by_task,
    cluster_bootstrap_paired,
    discordant_pairs_for_significance,
    exact_mcnemar,
    exact_sign_test,
    render_report,
    summarize_paired,
    summarize_paired_by,
)
from cdm.repair import PairedRepairOutcome, RepairAttempt, RepairOutcome, RepairVerification
from cdm.structured_edit import (
    PairedSelectionOutcome,
    SelectionAttempt,
    SelectionOutcome,
    SelectionVerification,
)
from cdm.synthetic import DecisionExample


def _repair_arm(success: bool, attempts: int) -> RepairOutcome:
    verdicts = [False] * (attempts - 1) + [success]
    return RepairOutcome(
        success,
        tuple(
            RepairAttempt("p", "o", RepairVerification(ok, "ok" if ok else "wrong_target"))
            for ok in verdicts
        ),
    )


def _selection_arm(success: bool, attempts: int) -> SelectionOutcome:
    verdicts = [False] * (attempts - 1) + [success]
    return SelectionOutcome(
        success,
        tuple(
            SelectionAttempt("p", "o", SelectionVerification(ok, "ok" if ok else "wrong_selection"))
            for ok in verdicts
        ),
    )


def _pair(base: tuple[bool, int], asst: tuple[bool, int], *, selection=False):
    if selection:
        return PairedSelectionOutcome(_selection_arm(*base), _selection_arm(*asst))
    return PairedRepairOutcome(_repair_arm(*base), _repair_arm(*asst))


def _example(source: str, task: str = "python.hard_masked_direct_call") -> DecisionExample:
    return DecisionExample(
        context="def caller(x):\n    return __CALL_TARGET__(x)\n",
        question="q",
        candidates=("a(x)", "b(x)"),
        answer_index=0,
        task=task,
        source=source,
    )


# (baseline, assisted) as (success, attempts_used)
PILOT = [
    _pair((True, 2), (True, 1)),    # both, assisted fewer
    _pair((True, 3), (True, 2)),    # both, assisted fewer
    _pair((True, 1), (True, 1)),    # both, same
    _pair((True, 2), (True, 2)),    # both, same
    _pair((False, 3), (True, 1)),   # assisted only
    _pair((False, 3), (True, 2)),   # assisted only
    _pair((False, 3), (True, 1)),   # assisted only
    _pair((False, 3), (True, 3)),   # assisted only
    _pair((True, 1), (False, 3)),   # baseline only
    _pair((False, 3), (False, 3)),  # neither
    _pair((False, 3), (False, 3)),  # neither
    _pair((False, 3), (False, 3)),  # neither
]


def test_summary_counts_match_hand_computed_report():
    summary = summarize_paired(PILOT)

    assert summary.tasks == 12
    assert summary.baseline.successes == 5
    assert summary.assisted.successes == 8
    assert summary.baseline.first_pass_successes == 2
    assert summary.assisted.first_pass_successes == 4
    assert summary.baseline.terminal_failures == 7
    assert summary.assisted.terminal_failures == 4
    assert summary.both_succeed == 4
    assert summary.assisted_only == 4
    assert summary.baseline_only == 1
    assert summary.neither == 3
    assert summary.correction_turn_deltas == (1, 1, 0, 0)
    assert summary.mean_correction_turn_delta == 0.5
    assert (summary.assisted_fewer, summary.assisted_same, summary.assisted_more) == (2, 2, 0)
    assert summary.success_rate_delta == pytest.approx(3 / 12)
    assert summary.mean_attempts_delta == pytest.approx((30 - 25) / 12)


def test_summary_accepts_structured_edit_outcomes():
    pairs = [_pair((True, 2), (True, 1), selection=True), _pair((False, 2), (True, 1), selection=True)]
    summary = summarize_paired(pairs)
    assert summary.both_succeed == 1
    assert summary.assisted_only == 1
    assert summary.correction_turn_deltas == (1,)


def test_summary_never_fabricates_delta_without_paired_success():
    summary = summarize_paired([_pair((False, 2), (True, 1)), _pair((True, 1), (False, 2))])
    assert summary.correction_turn_deltas == ()
    assert summary.mean_correction_turn_delta is None
    assert "not defined" in render_report(summary)


def test_summary_requires_outcomes():
    with pytest.raises(ValueError):
        summarize_paired([])


def test_exact_tests_match_binomial_values():
    summary = summarize_paired(PILOT)

    mcnemar = exact_mcnemar(summary)
    assert (mcnemar.favourable, mcnemar.unfavourable, mcnemar.ties) == (4, 1, 7)
    assert mcnemar.p_value == pytest.approx(2 * 6 / 32)  # P(X <= 1 | n=5)

    sign = exact_sign_test(summary)
    assert (sign.favourable, sign.unfavourable, sign.ties) == (2, 0, 2)
    assert sign.p_value == pytest.approx(0.5)


def test_exact_test_edge_cases():
    all_tied = summarize_paired([_pair((True, 1), (True, 1))] * 3)
    assert exact_mcnemar(all_tied).p_value == 1.0
    assert exact_sign_test(all_tied).p_value == 1.0

    seven_up = summarize_paired([_pair((False, 2), (True, 1))] * 7)
    assert exact_mcnemar(seven_up).p_value == pytest.approx(2 / 128)


def test_discordant_planning_helper():
    assert discordant_pairs_for_significance(1.0) == 6  # 2 * 0.5**6 < 0.05
    n = discordant_pairs_for_significance(0.8)
    assert 10 <= n <= 20
    with pytest.raises(ValueError):
        discordant_pairs_for_significance(0.5)


def test_group_summaries_by_task_and_namespace():
    examples = [
        _example("repo_a::x.py"),
        _example("repo_a::y.py", task="python.hard_masked_same_class_call"),
        _example("repo_b::z.py"),
    ]
    outcomes = [_pair((True, 2), (True, 1)), _pair((False, 3), (True, 1)), _pair((True, 1), (True, 1))]

    by_ns = summarize_paired_by(examples, outcomes, by_namespace)
    assert set(by_ns) == {"repo_a", "repo_b"}
    assert by_ns["repo_a"].tasks == 2
    assert by_ns["repo_b"].correction_turn_deltas == (0,)

    by_t = summarize_paired_by(examples, outcomes, by_task)
    assert by_t["python.hard_masked_same_class_call"].assisted_only == 1

    with pytest.raises(ValueError):
        summarize_paired_by([_example("no-namespace.py")], outcomes[:1], by_namespace)


def test_cluster_bootstrap_is_deterministic_and_covers_estimate():
    examples = [_example(f"repo::{i % 4}.py") for i in range(len(PILOT))]

    a = cluster_bootstrap_paired(examples, PILOT, bootstrap_samples=300, seed=1)
    b = cluster_bootstrap_paired(examples, PILOT, bootstrap_samples=300, seed=1)

    assert a == b
    assert a.statistic == "success_rate_delta"
    assert a.estimate == pytest.approx(3 / 12)
    assert a.lower <= a.estimate <= a.upper
    assert a.samples == 300

    turns = cluster_bootstrap_paired(
        examples, PILOT, statistic="mean_correction_turn_delta", bootstrap_samples=300
    )
    assert turns.estimate == 0.5
    assert turns.samples <= 300  # resamples with no paired success are skipped
    assert -1.0 <= turns.lower <= turns.upper <= 1.0


def test_cluster_bootstrap_resamples_files_not_tasks():
    # One file holds every task, so every resample is the full data set and the
    # interval must collapse onto the estimate.
    examples = [_example("repo::same.py") for _ in PILOT]
    interval = cluster_bootstrap_paired(examples, PILOT, bootstrap_samples=50)
    assert interval.lower == interval.upper == interval.estimate


def test_cluster_bootstrap_validation():
    examples = [_example(f"repo::{i}.py") for i in range(2)]
    pairs = [_pair((False, 2), (True, 1)), _pair((True, 1), (False, 2))]

    with pytest.raises(ValueError, match="undefined"):
        cluster_bootstrap_paired(examples, pairs, statistic="mean_correction_turn_delta")
    with pytest.raises(ValueError, match="statistic"):
        cluster_bootstrap_paired(examples, pairs, statistic="nope")
    with pytest.raises(ValueError, match="equal length"):
        cluster_bootstrap_paired(examples[:1], pairs)
    with pytest.raises(ValueError, match="provenance"):
        cluster_bootstrap_paired(
            [DecisionExample("c", "q", ("a",), 0, "t", None)] * 2, pairs
        )


def test_render_report_matches_experiment_note_shape():
    report = render_report(summarize_paired(PILOT))
    assert "| First-pass success | 2/12 (16.7%) | 4/12 (33.3%) |" in report
    assert "| Success within budget | 5/12 (41.7%) | 8/12 (66.7%) |" in report
    assert "| Terminal failures | 7/12 | 4/12 |" in report
    assert "- both succeed: 4" in report
    assert "assisted saved 0.50 correction turns" in report
    assert "fewer corrections on 2/4, the same on 2/4, and more on 0/4" in report
    assert "McNemar on 5 discordant tasks" in report
    assert "p = 0.375" in report
