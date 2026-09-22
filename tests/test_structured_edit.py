"""Tests for the E023 structured-edit harness."""
from __future__ import annotations

from cdm.structured_edit import (
    apply_structured_edit,
    parse_candidate_index,
    run_paired_selection,
    verify_selection,
)
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="""def caller(value):
    return __CALL_TARGET__(value)
""",
        question="Which candidate should replace __CALL_TARGET__?",
        candidates=(
            """normalize(value)
def normalize(value):
    return value.lower()
""",
            """parse(value)
def parse(value):
    return int(value)
""",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="test::example.py",
    )


def test_parse_candidate_index_variants():
    assert parse_candidate_index("1", 4) == 0
    assert parse_candidate_index("candidate 2", 4) == 1
    assert parse_candidate_index("Candidate 3:", 4) == 2
    assert parse_candidate_index("9", 4) is None
    assert parse_candidate_index("no number here", 4) is None


def test_apply_structured_edit_replaces_marker():
    example = _example()
    repaired = apply_structured_edit(example, 0)
    assert "__CALL_TARGET__" not in repaired
    assert "normalize" in repaired


def test_verify_selection_accepts_correct_index():
    example = _example()
    ok = verify_selection(example, "1")
    assert ok.valid and ok.selected_index == 0
    bad = verify_selection(example, "2")
    assert not bad.valid and bad.reason == "wrong_selection"


def test_paired_correct_recommendation_reduces_corrections():
    example = _example()

    def factory():
        state = {"n": 0}

        def generate(prompt: str) -> str:
            state["n"] += 1
            if "candidate 1 is recommended" in prompt.lower():
                return "1"
            # Baseline: wrong once, then recover after feedback.
            if "Deterministic verifier feedback:" in prompt:
                return "1"
            return "2"

        return generate

    paired = run_paired_selection(
        example,
        factory,
        recommendation_index=0,
        max_attempts=3,
    )
    assert paired.assisted.first_pass_success
    assert paired.baseline.success
    assert paired.correction_turn_delta is not None
    assert paired.correction_turn_delta >= 1


def test_unresolved_pair_has_null_delta():
    example = _example()

    def factory():
        def generate(prompt: str) -> str:
            return "2"  # always wrong

        return generate

    paired = run_paired_selection(
        example,
        factory,
        recommendation_index=0,
        max_attempts=2,
    )
    assert not paired.baseline.success
    assert not paired.assisted.success
    assert paired.correction_turn_delta is None
