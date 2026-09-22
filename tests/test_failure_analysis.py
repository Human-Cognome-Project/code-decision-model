from __future__ import annotations

import pytest

from cdm.failure_analysis import (
    failure_signature,
    render_failure_report,
    summarize_failures,
    summarize_failures_by,
)
from cdm.structured_edit import (
    PairedSelectionOutcome,
    SelectionAttempt,
    SelectionOutcome,
    SelectionVerification,
)
from cdm.synthetic import DecisionExample


def _example(source: str = "repo::x.py", answer: int = 0) -> DecisionExample:
    return DecisionExample(
        context="def caller(x):\n    return __CALL_TARGET__(x)\n",
        question="pick",
        candidates=("a(x)\ndef a(x): return x\n", "b(x)\ndef b(x): return x\n"),
        answer_index=answer,
        task="python.hard_masked_direct_call",
        source=source,
    )


def _outcome(
    assisted_steps: list[tuple[str, int | None, bool]],
    *,
    baseline_success: bool = False,
) -> PairedSelectionOutcome:
    def make(steps):
        attempts = tuple(
            SelectionAttempt(
                prompt="p",
                output="o",
                verification=SelectionVerification(valid, reason, selected),
            )
            for reason, selected, valid in steps
        )
        return SelectionOutcome(any(a.verification.valid for a in attempts), attempts)

    baseline = make([("ok", 0, True)] if baseline_success else [("wrong_selection", 1, False)])
    return PairedSelectionOutcome(baseline, make(assisted_steps))


def test_signature_marks_ignored_correct_recommendation():
    sig = failure_signature(
        _example(),
        _outcome([("wrong_selection", 1, False), ("wrong_selection", 1, False)]),
        0,
    )
    assert sig.recommendation_correct
    assert sig.ignored_correct_recommendation
    assert not sig.followed_wrong_recommendation
    assert sig.feedback_recovery_failed


def test_signature_marks_followed_wrong_recommendation():
    sig = failure_signature(
        _example(),
        _outcome([("wrong_selection", 1, False), ("wrong_selection", 1, False)]),
        1,
    )
    assert not sig.recommendation_correct
    assert sig.followed_recommendation is True
    assert sig.followed_wrong_recommendation


def test_unparseable_first_attempt_is_neither_followed_nor_ignored_by_index():
    sig = failure_signature(
        _example(),
        _outcome([("unparseable_selection", None, False), ("wrong_selection", 1, False)]),
        0,
    )
    assert sig.followed_recommendation is None
    assert sig.ignored_correct_recommendation


def test_summary_counts_orthogonal_failure_mechanisms():
    examples = [_example("a::x.py"), _example("b::y.py"), _example("b::z.py")]
    outcomes = [
        _outcome([("wrong_selection", 1, False), ("wrong_selection", 1, False)]),
        _outcome([("wrong_selection", 1, False), ("wrong_selection", 1, False)]),
        _outcome([("ok", 0, True)]),
    ]
    summary = summarize_failures(examples, outcomes, [0, 1, 0])
    assert summary.tasks == 3
    assert summary.assisted_failures == 2
    assert summary.wrong_recommendations == 1
    assert summary.correct_recommendations_ignored == 1
    assert summary.wrong_recommendations_followed == 1
    assert summary.feedback_recovery_failures == 2
    assert summary.assisted_failure_rate == pytest.approx(2 / 3)


def test_grouped_summary_and_report():
    examples = [_example("a::x.py"), _example("b::y.py")]
    outcomes = [
        _outcome([("wrong_selection", 1, False)]),
        _outcome([("ok", 0, True)]),
    ]
    grouped = summarize_failures_by(
        examples,
        outcomes,
        [0, 0],
        lambda e: e.source.split("::", 1)[0],
    )
    assert grouped["a"].assisted_failures == 1
    assert grouped["b"].assisted_failures == 0
    report = render_failure_report(summarize_failures(examples, outcomes, [0, 0]))
    assert "assisted terminal failures: 1 (50.0%)" in report
    assert "correct recommendations ignored" in report


def test_validation():
    with pytest.raises(ValueError, match="out of range"):
        failure_signature(_example(), _outcome([("ok", 0, True)]), 9)
    with pytest.raises(ValueError, match="equal length"):
        summarize_failures([_example()], [], [])
