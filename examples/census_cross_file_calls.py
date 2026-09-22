#!/usr/bin/env python3
"""E030 census: how much cross-file supervision a repository supplies.

Reports import-resolved cross-file call decisions next to the existing hard
same-file function and same-class method decisions, at the same candidate count,
so the new task's density can be judged against the tasks already in the frozen
protocol. No model download is required. The default root is this repository.

Run:

    python examples/census_cross_file_calls.py [ROOT] [--candidates N]
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import repository_hard_masked_call_examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--candidates", type=int, default=4)
    args = parser.parse_args()

    same_file = repository_hard_masked_call_examples(args.root, candidate_count=args.candidates)
    methods = repository_hard_masked_method_call_examples(args.root, candidate_count=args.candidates)
    cross = repository_hard_masked_cross_file_call_examples(args.root, candidate_count=args.candidates)

    print(f"root: {args.root}")
    print(f"candidates per decision: {args.candidates}")
    print(f"hard same-file function calls:   {len(same_file)}")
    print(f"hard same-class method calls:    {len(methods)}")
    print(f"hard cross-file function calls:  {len(cross)}")
    print()
    print("cross-file callers by source file:")
    for source, count in Counter(e.source for e in cross).most_common():
        print(f"  {count:4d}  {source}")


if __name__ == "__main__":
    main()
