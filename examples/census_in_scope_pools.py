#!/usr/bin/env python3
"""E040 census: how large is the real decision behind each hard task?

For every hard same-file and cross-file task in a repository, reports the size
of the candidate pool at two levels in distinct candidate renderings, how far
the E024 binding predicate prunes each, how that compares with the extractor's
shape-matched negatives, how many of the frozen task's own wrong candidates
are in the caller's scope, whether the target is in scope without the masked
call's own import line, and how many tasks are ambiguous at repository scale
because another function renders identically to the target:

- scope pool: module-level functions in the caller's file plus resolvable
  from-imports, caller excluded;
- repository pool: every top-level function in the repository, caller excluded.

No model download is required. The default root is this repository.

Run:

    python examples/census_in_scope_pools.py [ROOT] [--candidates N]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean, median

from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.repository import repository_hard_masked_call_examples
from cdm.scope import in_scope_pools, pool_census, pool_examples


def _line(label: str, values) -> str:
    values = list(values)
    return f"{label:<34} mean {mean(values):6.1f}   median {median(values):5.0f}   max {max(values):4d}"


def report(label: str, examples, scope) -> None:
    census = [c for c in (pool_census(e, scope) for e in examples) if c is not None]
    n = len(census)
    print(f"=== {label} ===")
    print(f"tasks:                              {len(examples)} (censused {n})")
    if not census:
        print()
        return
    print(f"protocol candidates per task:       {census[0].protocol_candidates}")
    print(f"consistency: target in scope / bindable / repo:  {sum(c.target_in_scope for c in census)}/{n}  "
          f"{sum(c.target_bindable_in_scope for c in census)}/{n}  {sum(c.target_in_repository for c in census)}/{n}")
    negatives = sum(c.protocol_candidates - 1 for c in census)
    print(f"protocol negatives in caller scope: {sum(c.protocol_negatives_in_scope for c in census)}/{negatives}")
    resolved = sum(c.scope_filter_resolves_protocol for c in census)
    print(f"scope filter alone resolves task:   {resolved}/{n} ({100.0 * resolved / n:.1f}%)")
    independent = sum(c.target_in_scope_independently for c in census)
    print(f"target in scope without its call:   {independent}/{n}")
    both = sum(c.scope_filter_resolves_protocol_independently for c in census)
    print(f"  scope filter resolves, too:       {both}/{n} ({100.0 * both / n:.1f}%)")
    print(_line("scope pool size:", (c.scope_size for c in census)))
    print(_line("  of which imported:", (c.scope_imported for c in census)))
    print(_line("  E024-bindable:", (c.scope_bindable for c in census)))
    print(_line("  same call shape as target:", (c.scope_shape_matched for c in census)))
    solved = sum(c.scope_solved_by_predicate for c in census)
    print(f"scope solved by predicate alone:    {solved}/{n} ({100.0 * solved / n:.1f}%)")
    at_most_protocol = sum(c.scope_bindable <= c.protocol_candidates for c in census)
    print(f"scope bindable <= protocol count:   {at_most_protocol}/{n} ({100.0 * at_most_protocol / n:.1f}%)")
    print(_line("repository pool size:", (c.repository_size for c in census)))
    print(_line("  E024-bindable:", (c.repository_bindable for c in census)))
    ambiguous = sum(not c.target_unique_in_repository for c in census)
    print(f"ambiguous at repository scale:      {ambiguous}/{n}")
    widened = pool_examples(examples, scope)
    repo_wide = pool_examples(examples, scope, level="repository")
    print(f"pool-complete tasks (scope):        {len(widened)}   mean candidates {mean(len(w.candidates) for w in widened):.1f}")
    print(f"pool-complete tasks (repository):   {len(repo_wide)}   mean candidates {mean(len(w.candidates) for w in repo_wide):.1f}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--candidates", type=int, default=4)
    args = parser.parse_args()
    scope = in_scope_pools(args.root)
    print(f"root: {args.root}")
    print(f"module-level functions: {len(scope.all_symbols)}")
    print()
    report("hard same-file function calls (E006)",
           repository_hard_masked_call_examples(args.root, candidate_count=args.candidates), scope)
    report("hard cross-file function calls (E030)",
           repository_hard_masked_cross_file_call_examples(args.root, candidate_count=args.candidates), scope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
