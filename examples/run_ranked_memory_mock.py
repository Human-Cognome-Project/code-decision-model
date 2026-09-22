#!/usr/bin/env python3
"""E032 mock: frozen loop vs rejection memory vs ranked re-recommendation.

Uses the E028-observed generator behaviour (always follow the recommendation;
without one, pick the lowest eligible number) so the three loops differ only in
what the decision layer says after a rejection. No model download is required.

Run:

    python examples/run_ranked_memory_mock.py
"""
from __future__ import annotations

from cdm.binding import CallSiteBindable
from cdm.ranked_memory import run_selection_loop_with_ranked_memory
from cdm.rejection_memory import run_selection_loop_with_rejection_memory
from cdm.structured_edit import run_selection_loop
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="def caller(x):\n    return __CALL_TARGET__(x, mode=1)\n",
        question="Which candidate should replace __CALL_TARGET__?",
        candidates=(
            "a(x, mode)\ndef a(x, mode=0):\n    return x\n",
            "b(x, mode)\ndef b(x, mode=0):\n    return x\n",
            "c(x, mode)\ndef c(x, mode=0):\n    return x\n",
            "d(x, flag)\ndef d(x, flag=0):\n    return x\n",
        ),
        answer_index=2,
        task="python.hard_masked_direct_call",
        source="mock::ranked.py",
    )


def follower(prompt: str) -> str:
    lower = prompt.lower()
    tag = " is recommended"
    if tag in lower:
        start = lower.rfind("candidate ", 0, lower.index(tag)) + len("candidate ")
        return lower[start:lower.index(tag)].strip()
    for line in prompt.splitlines():
        if line.startswith("Reply with one candidate number from: "):
            return line.split("from:")[1].split(",")[0].strip(" .")
    return "1"


def main() -> None:
    example = _example()

    print("=== wrong top recommendation, correct second (ranking 1,3,2,4) ===")
    frozen = run_selection_loop(example, follower, recommendation_index=0, max_attempts=2)
    memory = run_selection_loop_with_rejection_memory(example, follower, recommendation_index=0, max_attempts=2)
    ranked = run_selection_loop_with_ranked_memory(example, follower, ranking=(0, 2, 1, 3), max_attempts=2)
    print(f"E027 frozen     success={frozen.success} outputs={[a.output for a in frozen.attempts]}")
    print(f"E029 memory     success={memory.outcome.success} outputs={[a.output for a in memory.outcome.attempts]}")
    print(f"E032 ranked     success={ranked.outcome.success} outputs={[a.output for a in ranked.outcome.attempts]} recommendations={ranked.recommendations}")
    assert not frozen.success and not memory.outcome.success and ranked.outcome.success

    print()
    print("=== top pick vetoed by the E024 predicate (ranking 4,3,1,2) ===")
    ungated = run_selection_loop_with_ranked_memory(example, follower, ranking=(3, 2, 0, 1), max_attempts=2)
    gated = run_selection_loop_with_ranked_memory(
        example, follower, ranking=(3, 2, 0, 1), constraints=[CallSiteBindable()], max_attempts=2
    )
    print(f"no constraint   first_pass={ungated.outcome.first_pass_success} recommendations={ungated.recommendations}")
    print(f"predicate-gated first_pass={gated.outcome.first_pass_success} recommendations={gated.recommendations} allowed={gated.allowed}")
    assert not ungated.outcome.first_pass_success and gated.outcome.first_pass_success

    print()
    print("E032 mock checks passed")


if __name__ == "__main__":
    main()
