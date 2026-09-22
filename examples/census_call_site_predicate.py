#!/usr/bin/env python3
"""E023 census: what the call-site bindability predicate removes, and what it must not.

Runs the deterministic predicate over machine-labelled masked-call corpora built
from a repository root and reports, per corpus:

- how many examples the predicate touches at all;
- the mean number of surviving candidates;
- the expected accuracy of "predicate + uniform choice" versus uniform choice;
- the number of machine-labelled targets the predicate vetoed (must be zero).

No model download is required. The default root is this repository.

Run:

    python examples/census_call_site_predicate.py [ROOT]
"""
from __future__ import annotations

import sys
from pathlib import Path

from cdm.binding import CallSiteBindable
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import (
    repository_hard_masked_call_examples,
    repository_masked_call_examples,
)


def census(label: str, examples) -> int:
    predicate = CallSiteBindable()
    touched = 0
    survivors_total = 0
    predicate_expected = 0.0
    uniform_expected = 0.0
    truth_vetoed = 0

    for example in examples:
        result = predicate.check(example.context, example.question, example.candidates)
        survivors = sum(result.allowed)
        if not result.allowed[example.answer_index]:
            truth_vetoed += 1
        if survivors < len(example.candidates):
            touched += 1
        survivors_total += survivors
        predicate_expected += 1.0 / survivors if survivors else 0.0
        uniform_expected += 1.0 / len(example.candidates)

    n = len(examples)
    print(f"=== {label} ===")
    print(f"examples:                     {n}")
    if n:
        print(f"examples with any veto:       {touched} ({100.0 * touched / n:.1f}%)")
        print(f"mean surviving candidates:    {survivors_total / n:.2f}")
        print(f"uniform expected accuracy:    {100.0 * uniform_expected / n:.1f}%")
        print(f"predicate+uniform expected:   {100.0 * predicate_expected / n:.1f}%")
    print(f"machine-labelled truth vetoed: {truth_vetoed}")
    print()
    return truth_vetoed


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    vetoed = 0
    vetoed += census(
        "E005 masked direct call (repository-wide candidates)",
        repository_masked_call_examples(root, max_candidates=16),
    )
    vetoed += census(
        "E006 hard masked direct call (shape-controlled)",
        repository_hard_masked_call_examples(root, candidate_count=4),
    )
    vetoed += census(
        "E015 hard masked same-class method call (shape-controlled)",
        repository_hard_masked_method_call_examples(root, candidate_count=4),
    )
    if vetoed:
        print(f"UNSOUND: predicate vetoed {vetoed} machine-labelled targets")
        return 1
    print("predicate soundness holds: no machine-labelled target was vetoed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
