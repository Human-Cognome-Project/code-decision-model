#!/usr/bin/env python3
"""E023 mock: structured-edit paired measurement without a real generator."""
from __future__ import annotations

from cdm.structured_edit import run_paired_selection
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="""def caller(value):
    prepared = value.strip()
    return __CALL_TARGET__(prepared)
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
        source="mock::structured.py",
    )


def _follower_factory(example: DecisionExample):
    def generate(prompt: str) -> str:
        lower = prompt.lower()
        if "candidate 1 is recommended" in lower:
            return "1"
        if "candidate 2 is recommended" in lower:
            return "2"
        if "deterministic verifier feedback:" in lower:
            return str(example.answer_index + 1)
        return "2"  # wrong first guess without recommendation

    return generate


def main() -> None:
    example = _example()
    good = run_paired_selection(
        example,
        lambda: _follower_factory(example),
        recommendation_index=0,
        max_attempts=3,
    )
    print(
        "correct_rec",
        "base", good.baseline.correction_turns,
        "asst", good.assisted.correction_turns,
        "delta", good.correction_turn_delta,
    )
    bad = run_paired_selection(
        example,
        lambda: _follower_factory(example),
        recommendation_index=1,
        max_attempts=3,
    )
    print(
        "wrong_rec",
        "base", bad.baseline.success, bad.baseline.attempts_used,
        "asst", bad.assisted.success, bad.assisted.attempts_used,
        "delta", bad.correction_turn_delta,
    )
    assert good.correction_turn_delta is not None
    assert good.correction_turn_delta >= 1
    print("structured-edit mock checks passed")


if __name__ == "__main__":
    main()
