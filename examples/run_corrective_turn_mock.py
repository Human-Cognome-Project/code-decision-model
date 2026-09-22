#!/usr/bin/env python3
"""E022 mock: exercise the corrective-turn harness without a real generator.

Two deterministic generators demonstrate the measurement contract:

- oracle_after_feedback: fails first attempt, then emits the true repair.
- stubborn_wrong: always emits a valid but incorrect candidate.

Run:

    python examples/run_corrective_turn_mock.py
"""
from __future__ import annotations

from cdm.repair import (
    candidate_symbol,
    expected_repair_source,
    run_paired_repair,
)
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="""def caller(value):
    prepared = value.strip()
    return __CALL_TARGET__(prepared)
""",
        question="Which candidate definition should replace __CALL_TARGET__?",
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
        source="mock::example.py",
    )


def _oracle_after_feedback_factory(example: DecisionExample):
    """Fail once, then return the exact expected repair (uses feedback presence)."""
    expected = expected_repair_source(example)
    state = {"seen_feedback": False}

    def generate(prompt: str) -> str:
        if "Deterministic verifier feedback:" in prompt:
            state["seen_feedback"] = True
            return expected
        # First attempt: leave the placeholder so the verifier rejects it.
        return example.context

    return generate


def _stubborn_wrong_factory(example: DecisionExample):
    """Always emit a wrong but syntactically valid repair."""
    wrong_index = 1 if example.answer_index == 0 else 0
    wrong_name = candidate_symbol(example.candidates[wrong_index])
    # Build a minimal wrong repair by swapping the marker for the wrong symbol.
    wrong_source = example.context.replace("__CALL_TARGET__", wrong_name)

    def generate(prompt: str) -> str:
        return wrong_source

    return generate


def _report(label: str, paired) -> None:
    print(f"=== {label} ===")
    print(
        f"baseline  success={paired.baseline.success} "
        f"attempts={paired.baseline.attempts_used} "
        f"corrections={paired.baseline.correction_turns}"
    )
    print(
        f"assisted  success={paired.assisted.success} "
        f"attempts={paired.assisted.attempts_used} "
        f"corrections={paired.assisted.correction_turns}"
    )
    print(f"success_delta={paired.success_delta}")
    print(f"correction_turn_delta={paired.correction_turn_delta}")
    print()


def main() -> None:
    example = _example()
    true_index = example.answer_index

    # Positive case: recommendation is correct; oracle needs one correction.
    paired_oracle = run_paired_repair(
        example,
        lambda: _oracle_after_feedback_factory(example),
        recommendation_index=true_index,
        max_attempts=3,
    )
    _report("oracle_after_feedback (correct recommendation)", paired_oracle)

    # Negative case: both arms fail; delta must stay None.
    paired_stubborn = run_paired_repair(
        example,
        lambda: _stubborn_wrong_factory(example),
        recommendation_index=true_index,
        max_attempts=3,
    )
    _report("stubborn_wrong (both fail)", paired_stubborn)

    # Sanity: assisted should not invent a delta when neither succeeds.
    assert paired_stubborn.correction_turn_delta is None
    # Oracle should succeed on both arms and show a non-negative delta.
    assert paired_oracle.baseline.success and paired_oracle.assisted.success
    assert paired_oracle.correction_turn_delta is not None
    assert paired_oracle.correction_turn_delta >= 0

    print("mock E022 checks passed")


if __name__ == "__main__":
    main()
