#!/usr/bin/env python3
"""E034 census: perturbation coverage and the model-free predicate baseline.

For each hard task family, reports how many decisions admit a restorable
argument perturbation, which perturbation types apply, and how far E024
bindability alone narrows the single-operation plan space:

- plans that bind (candidate x operation);
- decisions where the restoring plan is the only binding plan (solved by
  predicate alone);
- decisions where bindability leaves exactly one binding plan per candidate,
  so the ranker's choice decides the outcome.

No model download is required. The default root is this repository.

Run:

    python examples/census_argument_ops.py [ROOT]
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from cdm.argument_ops import argument_repair_examples, perturbations_for, predicate_search
from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import repository_hard_masked_call_examples


def report(label: str, examples) -> None:
    kinds = Counter(k for e in examples for k in perturbations_for(e))
    items = argument_repair_examples(examples, seed=0)
    chosen = Counter(item.perturbation for item in items)
    print(f"=== {label} ===")
    print(f"decisions:                    {len(examples)}")
    print(f"perturbable decisions:        {len(items)}")
    if kinds:
        print("applicable perturbations:     " + ", ".join(f"{k}: {v}" for k, v in sorted(kinds.items())))
        print("chosen (seed 0):              " + ", ".join(f"{k}: {v}" for k, v in sorted(chosen.items())))
    if items:
        binding_counts = []
        unique = 0
        one_per_candidate = 0
        restoring_present = 0
        for item in items:
            plans = predicate_search(item)
            binding_counts.append(len(plans))
            restoring_present += item.restoring_plan in plans
            unique += len(plans) == 1 and plans[0] == item.restoring_plan
            by_candidate = Counter(p.candidate_index for p in plans)
            one_per_candidate += bool(by_candidate) and max(by_candidate.values()) == 1
        n = len(items)
        print(f"mean binding single-op plans: {sum(binding_counts) / n:.2f}")
        print(f"restoring plan binds:         {restoring_present}/{n}")
        print(f"solved by predicate alone:    {unique}/{n} ({100.0 * unique / n:.1f}%)")
        print(f"one binding plan per cand.:   {one_per_candidate}/{n} ({100.0 * one_per_candidate / n:.1f}%)")
    print()


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    report("hard same-file function calls (E006)", repository_hard_masked_call_examples(root, candidate_count=4))
    report("hard same-class method calls (E015)", repository_hard_masked_method_call_examples(root, candidate_count=4))
    report("hard cross-file function calls (E030)", repository_hard_masked_cross_file_call_examples(root, candidate_count=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
