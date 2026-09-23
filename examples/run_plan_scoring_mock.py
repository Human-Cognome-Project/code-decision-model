#!/usr/bin/env python3
"""E035 mock: constrained plan scoring over the E034 plan space.

Runs the E035 loop on this repository's E034 tasks with three model-free
scorers, so the harness, the chance baselines, and the position-prior
diagnostic can be checked without a model download:

- constant: every plan scores the same, which reproduces E034's observed
  attractor ``candidate 1; keep`` exactly (0 exact);
- position: prefers whatever is shown first, with and without cyclic shifts,
  to show the shift control cancelling a pure position preference;
- oracle: prefers the plan naming the target symbol with the restoring
  operation, a content preference that survives shifts.

With ``--hf`` the pinned Qwen scorer is used instead on the first ``--tasks``
tasks (requires ``pip install -e '.[hf]'`` and a model fetch). That is a smoke
run, not the preregistered pilot.

Run:

    python examples/run_plan_scoring_mock.py [--hf] [--tasks N] [--shifts K]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cdm.argument_ops import argument_repair_examples
from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.plan_scoring import (
    ContinuationScore,
    chance_baselines,
    rank_plans,
    run_plan_scoring_loop,
    top_candidate_histogram,
)
from cdm.repair import candidate_symbol
from cdm.repository import repository_hard_masked_call_examples


class ConstantScorer:
    def __call__(self, prompt, continuations):
        return [ContinuationScore(-1.0, 4) for _ in continuations]


class PositionScorer:
    def __call__(self, prompt, continuations):
        return [ContinuationScore(0.0 if c.startswith("candidate 1;") else -5.0, 4) for c in continuations]


class OracleScorer:
    """Label-aware by construction: it exists only to show the harness credits a correct ranking."""

    def __init__(self, symbol: str, op: str):
        self.symbol, self.op = symbol, op

    def __call__(self, prompt, continuations):
        sections = re.split(r"\nCandidate (\d+):\n", prompt)
        shown = {int(sections[i]): sections[i + 1] for i in range(1, len(sections) - 1, 2)}
        out = []
        for c in continuations:
            k = int(c.split(";")[0].split()[1])
            good = shown[k].splitlines()[0].startswith(self.symbol + "(") and c.split(";")[1].strip() == self.op
            out.append(ContinuationScore(0.0 if good else -5.0, 4))
        return out


def report(label, items, make_scorer, *, shifts=1, max_attempts=3):
    first = exact = 0
    turns = []
    rankings = []
    for item in items:
        scorer = make_scorer(item)
        ranked = rank_plans(item, scorer, shifts=shifts)
        rankings.append(ranked)
        outcome = run_plan_scoring_loop(item, scorer, shifts=shifts, max_attempts=max_attempts)
        first += outcome.first_pass_success
        exact += outcome.success
        if outcome.success:
            turns.append(outcome.correction_turns)
    n = len(items)
    count = len(items[0].example.candidates)
    hist = top_candidate_histogram(rankings, count)
    mean_turns = sum(turns) / len(turns) if turns else float("nan")
    print(f"{label:<28} first-pass {first:>3}/{n}   within {max_attempts} attempts {exact:>3}/{n}   "
          f"mean correction turns {mean_turns:.2f}   top-ranked candidate position {hist}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hf", action="store_true", help="use the pinned Qwen scorer (downloads weights)")
    parser.add_argument("--tasks", type=int, default=8, help="tasks for the --hf smoke run")
    parser.add_argument("--shifts", type=int, default=4)
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv[1:])
    root = Path(args.root)

    examples = [
        *repository_hard_masked_call_examples(root, candidate_count=4),
        *repository_hard_masked_method_call_examples(root, candidate_count=4),
        *repository_hard_masked_cross_file_call_examples(root, candidate_count=4),
    ]
    items = argument_repair_examples(examples, seed=0)
    n = len(items)
    chance = [chance_baselines(item, recommendation_index=item.example.answer_index) for item in items]
    print(f"E034 tasks on this repository: {n}")
    print(f"expected exact success, uniform over plan space:              {sum(c.uniform for c in chance):.2f}/{n}")
    print(f"expected exact success, uniform over binding plans:           {sum(c.feasible_uniform for c in chance):.2f}/{n}")
    print(f"expected exact success, binding plans of a correct rec.:      {sum(c.recommended_feasible_uniform for c in chance):.2f}/{n}")
    print(f"E034 attractor 'candidate 1; keep':                           {sum(c.position_prior for c in chance):.0f}/{n}")
    print()

    if args.hf:
        try:
            from cdm.plan_scoring import make_hf_plan_scorer
            factory = make_hf_plan_scorer()
            scorer = factory()
        except ImportError as exc:
            print("hf extra not installed:", exc)
            return 2
        except Exception as exc:  # noqa: BLE001 - smoke path reports any load error
            print("model load failed:", type(exc).__name__, exc)
            return 3
        subset = items[: args.tasks]
        print(f"=== pinned Qwen scorer, first {len(subset)} tasks (smoke, not the pilot) ===")
        report("qwen, no shifts", subset, lambda item: scorer, shifts=1)
        report(f"qwen, {args.shifts} shifts", subset, lambda item: scorer, shifts=args.shifts)
        print(f"uncached boundary fallbacks: {scorer.uncached_fallbacks}")
        return 0

    print("=== model-free scorers ===")
    report("constant (E034 attractor)", items, lambda item: ConstantScorer())
    report("position, no shifts", items, lambda item: PositionScorer())
    report(f"position, {args.shifts} shifts", items, lambda item: PositionScorer(), shifts=args.shifts)
    oracle = lambda item: OracleScorer(  # noqa: E731
        candidate_symbol(item.example.candidates[item.example.answer_index]),
        " ".join(item.restoring_plan.operation),
    )
    report("oracle, no shifts", items, oracle)
    report(f"oracle, {args.shifts} shifts", items, oracle, shifts=args.shifts)
    print()
    print("E035 mock checks: the constant scorer reproduces the attractor; under shifts a pure position preference\n"
          "ties every plan and the rank falls back to plan-space order (still candidate 1); the oracle is credited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
