#!/usr/bin/env python3
"""E022 mock: exercise the corrective-turn harness without a real generator.

Deterministic generators demonstrate the measurement contract:

- recommendation_follower: uses a recommended candidate on the first attempt
  when present; otherwise fails once and recovers from verifier feedback.
- stubborn_wrong: always emits a valid but incorrect candidate.

Run:

    python examples/run_corrective_turn_mock.py
"""
from __future__ import annotations

import re

from cdm.repair import (
    candidate_symbol,
    expected_repair_source,
    run_paired_repair,
)
from cdm.synthetic import DecisionExample

_RECOMMENDATION = re.compile(
    r"candidate (\d+) is recommended",
    re.IGNORECASE,
)


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


def _repair_with(example: DecisionExample, candidate_index: int) -> str:
    name = candidate_symbol(example.candidates[candidate_index])
    return example.context.replace("__CALL_TARGET__", name)


def _recommendation_follower_factory(example: DecisionExample):
    """Prefer a stated recommendation; otherwise recover after feedback."""

    expected = expected_repair_source(example)
    true_index = example.answer_index

    def generate(prompt: str) -> str:
        match = _RECOMMENDATION.search(prompt)
        if match is not None:
            # Trust the fallible recommendation on the first pass.
            index = int(match.group(1)) - 1
            if 0 <= index < len(example.candidates):
                return _repair_with(example, index)

        if "Deterministic verifier feedback:" in prompt:
            return expected

        # No recommendation and no feedback yet: leave the placeholder.
        return example.context

    return generate


def _stubborn_wrong_factory(example: DecisionExample):
    """Always emit a wrong but syntactically valid repair."""
    wrong_index = 1 if example.answer_index == 0 else 0
    wrong_source = _repair_with(example, wrong_index)

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
    wrong_index = 1 if true_index == 0 else 0

    # Correct recommendation: assisted should first-pass; baseline needs a correction.
    paired_good = run_paired_repair(
        example,
        lambda: _recommendation_follower_factory(example),
        recommendation_index=true_index,
        max_attempts=3,
    )
    _report("recommendation_follower (correct recommendation)", paired_good)

    # Wrong recommendation: assisted may be harmed; harness must still report honestly.
    paired_bad = run_paired_repair(
        example,
        lambda: _recommendation_follower_factory(example),
        recommendation_index=wrong_index,
        max_attempts=3,
    )
    _report("recommendation_follower (wrong recommendation)", paired_bad)

    # Both arms fail; delta must stay None.
    paired_stubborn = run_paired_repair(
        example,
        lambda: _stubborn_wrong_factory(example),
        recommendation_index=true_index,
        max_attempts=3,
    )
    _report("stubborn_wrong (both fail)", paired_stubborn)

    assert paired_stubborn.correction_turn_delta is None
    assert paired_good.baseline.success and paired_good.assisted.success
    assert paired_good.assisted.first_pass_success
    assert paired_good.correction_turn_delta is not None
    assert paired_good.correction_turn_delta >= 1
    # Wrong recommendation must be allowed to hurt the assisted arm.
    assert paired_bad.assisted.attempts_used >= paired_good.assisted.attempts_used

    print("mock E022 checks passed")


if __name__ == "__main__":
    main()
