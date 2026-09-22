#!/usr/bin/env python3
"""E033 mock: call-expression intent under deterministic verification.

Shows, without a model download, how the verifier orders its checks on a
generated fragment: parse, candidate membership, E024 bindability, then AST
equivalence with the machine-labelled repair. Also runs one paired loop with a
recommendation-following generator.

Run:

    python examples/run_call_intent_mock.py
"""
from __future__ import annotations

from cdm.call_intent import (
    feedback_for_call_intent,
    masked_call_source,
    run_paired_call_intent,
    verify_call_intent,
)
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="def caller(value):\n    prepared = value.strip()\n    return __CALL_TARGET__(prepared, strict=True)\n",
        question="Which call should replace __CALL_TARGET__?",
        candidates=(
            "normalize(value, strict)\ndef normalize(value, strict=False):\n    return value.lower()\n",
            "parse(value, strict)\ndef parse(value, strict=False):\n    return int(value)\n",
            "emit(value, mode)\ndef emit(value, mode=0):\n    return str(value)\n",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="mock::intent.py",
    )


def main() -> None:
    example = _example()
    print("masked call:", masked_call_source(example))
    print()
    for output in [
        "def caller(value): ...",
        "unknown(prepared, strict=True)",
        "emit(prepared, strict=True)",
        "parse(prepared, strict=True)",
        "normalize(prepared)",
        "normalize(prepared, strict=True)",
    ]:
        result = verify_call_intent(example, output)
        print(f"{output!r:40} -> {result.reason:24} {feedback_for_call_intent(result)[:60] if not result.valid else ''}")

    args = masked_call_source(example).split("(", 1)[1]

    def factory():
        calls = {"n": 0}

        def generate(prompt: str) -> str:
            calls["n"] += 1
            if "candidate 1 is recommended" in prompt.lower():
                return "normalize(" + args
            return ("parse(" if calls["n"] == 1 else "normalize(") + args

        return generate

    paired = run_paired_call_intent(example, factory, recommendation_index=0, max_attempts=3)
    print()
    print(f"baseline corrections={paired.baseline.correction_turns} assisted corrections={paired.assisted.correction_turns} delta={paired.correction_turn_delta}")
    assert paired.correction_turn_delta == 1
    print("E033 mock checks passed")


if __name__ == "__main__":
    main()
