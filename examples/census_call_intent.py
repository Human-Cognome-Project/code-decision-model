#!/usr/bin/env python3
"""E033 census: how many hard masked-call decisions have a single call site.

The call-intent task replaces exactly one masked call with a generated
expression, so decisions whose caller invokes the masked target more than once
are ineligible. Reports eligibility per task family and the distribution of
argument counts at the masked call site, which sets the difficulty of the
generation surface. No model download is required.

Run:

    python examples/census_call_intent.py [ROOT]
"""
from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path

from cdm.call_intent import eligible, masked_call_source
from cdm.repair import candidate_symbol
from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import repository_hard_masked_call_examples


def _argument_count(source: str) -> int:
    call = ast.parse(source, mode="eval").body
    return len(call.args) + len(call.keywords)


def report(label: str, examples) -> None:
    ok = [e for e in examples if eligible(e)]
    print(f"=== {label} ===")
    print(f"decisions:              {len(examples)}")
    if examples:
        print(f"single call site:       {len(ok)} ({100.0 * len(ok) / len(examples):.1f}%)")
    duplicated = sum(
        sum(candidate_symbol(c) == candidate_symbol(e.candidates[e.answer_index]) for c in e.candidates) > 1
        for e in ok
    )
    if ok:
        print(f"answer name duplicated:  {duplicated} (unwinnable by name)")
    counts = Counter(_argument_count(masked_call_source(e)) for e in ok)
    if counts:
        dist = ", ".join(f"{k} args: {v}" for k, v in sorted(counts.items()))
        print(f"masked-call arguments:  {dist}")
    print()


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parents[1]
    report("hard same-file function calls (E006)", repository_hard_masked_call_examples(root, candidate_count=4))
    report("hard same-class method calls (E015)", repository_hard_masked_method_call_examples(root, candidate_count=4))
    report("hard cross-file function calls (E030)", repository_hard_masked_cross_file_call_examples(root, candidate_count=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
