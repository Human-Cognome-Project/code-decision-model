#!/usr/bin/env python3
"""E034 census: perturbation coverage, leakage control, and the model-free
predicate baseline.

For each hard task family, reports how many decisions admit a restorable
argument perturbation, which perturbation types apply, whether the visible
corruption is invariant to relabelling the answer, and how far E024
bindability alone narrows the plan space (candidate x single operation):

- mean size of the plan space and of its binding subset;
- mean number of candidates left with at least one binding plan;
- decisions where the restoring plan is the only binding plan (solved by
  predicate alone);
- decisions where every candidate has exactly one binding plan (pure
  selection: the ranker's choice alone decides the outcome);
- decisions where no surviving candidate has more than one binding plan
  (weaker; candidates with zero plans are excluded, so this is not pure
  selection).

No model download is required. The default root is this repository.

Run:

    python examples/census_argument_ops.py [ROOT]
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from cdm.argument_ops import (
    argument_repair_example,
    argument_repair_examples,
    corruption_is_label_invariant,
    perturbations_for,
    predicate_census,
)
from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import repository_hard_masked_call_examples


def report(label: str, examples) -> None:
    kinds = Counter(k for e in examples for k in perturbations_for(e))
    items = argument_repair_examples(examples, seed=0)
    chosen = Counter(item.perturbation for item in items)
    print(f"=== {label} ===")
    print(f"decisions:                        {len(examples)}")
    print(f"perturbable decisions:            {len(items)}")
    if kinds:
        print("applicable perturbations:         " + ", ".join(f"{k}: {v}" for k, v in sorted(kinds.items())))
        print("chosen (seed 0):                  " + ", ".join(f"{k}: {v}" for k, v in sorted(chosen.items())))
    if items:
        invariant = sum(corruption_is_label_invariant(e) for e in examples if argument_repair_example(e, seed=0))
        census = [predicate_census(item) for item in items]
        n = len(items)
        space = sum(c.plan_space_size for c in census) / n
        binding = sum(c.binding_plans for c in census) / n
        survivors = sum(c.surviving_candidates for c in census) / n
        restoring = sum(c.restoring_plan_binds for c in census)
        solved = sum(c.solved_by_predicate for c in census)
        pure = sum(c.pure_selection for c in census)
        weak = sum(c.at_most_one_per_survivor for c in census)
        print(f"label-invariant corruption:       {invariant}/{n}")
        print(f"mean plan space (cand x op):      {space:.2f}")
        print(f"mean binding plans:               {binding:.2f}")
        print(f"mean surviving candidates:        {survivors:.2f} of {len(items[0].example.candidates)}")
        print(f"restoring plan binds:             {restoring}/{n}")
        print(f"solved by predicate alone:        {solved}/{n} ({100.0 * solved / n:.1f}%)")
        print(f"pure selection (1 plan / cand.):  {pure}/{n} ({100.0 * pure / n:.1f}%)")
        print(f"<=1 plan per surviving cand.:     {weak}/{n} ({100.0 * weak / n:.1f}%)")
    print()


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    report("hard same-file function calls (E006)", repository_hard_masked_call_examples(root, candidate_count=4))
    report("hard same-class method calls (E015)", repository_hard_masked_method_call_examples(root, candidate_count=4))
    report("hard cross-file function calls (E030)", repository_hard_masked_cross_file_call_examples(root, candidate_count=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
