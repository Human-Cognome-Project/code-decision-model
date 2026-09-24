#!/usr/bin/env python3
"""E044 census: how often does the import neighbourhood contain a cross-file target?

For every E030 hard cross-file task in each repository, the import
neighbourhood is every top-level function in the repository files that the
caller's file imports from, with the target's own import name removed. The
census reports target recall, pool size after E024 bindability and rendering
deduplication, and the recall a uniform random subset of the bindable
repository pool of the same size would have. The count of pools of at most 32
candidates refers to E043's preregistered shortlist budget; it is descriptive
and selects nothing.

Tasks whose target renders like another bindable repository function are
ambiguous and are counted but not censused, as in E042 and E043.

No model download is required. The default root is this repository.

Run:

    python examples/census_import_neighbourhoods.py [ROOT ...] [--body-chars N]
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import mean, median

from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.neighbourhood import VARIANTS, import_neighbourhoods, neighbourhood_census


def report(label: str, censuses) -> None:
    n = len(censuses)
    if not n:
        print(f"{label:<12} no censused tasks")
        return
    for variant in VARIANTS:
        hits = sum(getattr(c, f"target_in_{variant}_pool") for c in censuses)
        sizes = [getattr(c, f"{variant}_bindable") for c in censuses]
        uniform = sum(getattr(c, f"{variant}_uniform_recall") for c in censuses)
        within = sum(size <= 32 for size in sizes)
        hit_within = sum(
            getattr(c, f"target_in_{variant}_pool") and getattr(c, f"{variant}_bindable") <= 32 for c in censuses
        )
        print(
            f"{label:<12} {variant:<11} recall {hits:>4}/{n:<4} ({100.0 * hits / n:5.1f}%)   "
            f"uniform same size {uniform:6.1f}   bindable pool mean {mean(sizes):5.1f} "
            f"median {median(sizes):4.0f} max {max(sizes):4d}   pool <= 32: {within}/{n}, with target {hit_within}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="*", type=Path, default=[Path(__file__).resolve().parents[1]])
    parser.add_argument("--body-chars", type=int, default=768)
    parser.add_argument("--candidates", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    everything = []
    for root in args.roots:
        examples = repository_hard_masked_cross_file_call_examples(
            root, candidate_count=args.candidates, candidate_body_chars=args.body_chars, seed=args.seed
        )
        neighbourhoods = import_neighbourhoods(root)
        raw = [neighbourhood_census(e, neighbourhoods, body_chars=args.body_chars) for e in examples]
        missing = sum(c is None for c in raw)
        ambiguous = sum(1 for c in raw if c is not None and not c.target_unique_in_repository)
        kept = [c for c in raw if c is not None and c.target_unique_in_repository]
        name = root.resolve().name
        print(f"{name}: {len(examples)} cross-file tasks, {ambiguous} ambiguous, {missing} without a binding import")
        if kept:
            print(f"{'':<12} repository bindable mean {mean(c.repository_bindable for c in kept):.1f} "
                  f"median {median(c.repository_bindable for c in kept):.0f}")
        report(name, kept)
        everything.extend(kept)
    if len(args.roots) > 1:
        print()
        report("total", everything)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
