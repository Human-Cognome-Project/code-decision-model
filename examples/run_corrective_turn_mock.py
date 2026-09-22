#!/usr/bin/env python3
"""E021 companion: exercise the corrective-turn harness without a real model.

Two deterministic generators demonstrate the paired measurement contract:

- recommendation_sensitive: baseline needs one correction, assisted succeeds first try.
- stubborn_wrong: both arms fail and no correction-turn delta is fabricated.

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


def _recommendation_sensitive_factory(example: DecisionExample):
    """Use a correct recommendation immediately; otherwise require feedback."""
    expected = expected_repair_source(example)
    expected_marker = f"candidate {example.answer_index + 1} is recommended"

    def generate(prompt: str) -> str:
        if expected_marker in prompt:
            return expected
        if "Deterministic verifier feedback:" in prompt:
            return expected
        return example.context

    return generate


def _stubborn_wrong_factory(example: DecisionExample):
    """Always emit a wrong but syntactically valid repair."""
    wrong_index = 1 if example.answer_index == 0 else 0
    wrong_name = candidate_symbol(example.candidates[wrong_index])
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

    paired_positive = run_paired_repair(
        example,
        lambda: _recommendation_sensitive_factory(example),
        recommendation_index=true_index,
        max_attempts=3,
    )
    _report(
        "recommendation_sensitive (correct recommendation)",
        paired_positive,
    )

    paired_stubborn = run_paired_repair(
        example,
        lambda: _stubborn_wrong_factory(example),
        recommendation_index=true_index,
        max_attempts=3,
    )
    _report("stubborn_wrong (both fail)", paired_stubborn)

    assert paired_positive.baseline.success
    assert paired_positive.assisted.success
    assert paired_positive.baseline.correction_turns == 1
    assert paired_positive.assisted.correction_turns == 0
    assert paired_positive.correction_turn_delta == 1

    assert not paired_stubborn.baseline.success
    assert not paired_stubborn.assisted.success
    assert paired_stubborn.correction_turn_delta is None

    print("E021 companion mock checks passed")


if __name__ == "__main__":
    main()
