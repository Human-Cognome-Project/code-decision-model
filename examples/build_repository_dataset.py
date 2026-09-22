"""Build a machine-labeled decision dataset from a local Python repository."""
from __future__ import annotations

import argparse
from pathlib import Path

from cdm.repository import (
    repository_call_examples,
    split_repository_examples,
    write_jsonl_dataset,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-candidates", type=int, default=16)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    examples = repository_call_examples(
        args.repository,
        max_candidates=args.max_candidates,
        seed=args.seed,
        strict=args.strict,
    )
    dataset = split_repository_examples(examples, seed=args.seed)
    paths = write_jsonl_dataset(dataset, args.output)

    print(f"examples: {len(examples)}")
    for split, size in dataset.sizes().items():
        print(f"{split}: {size} -> {paths[split]}")


if __name__ == "__main__":
    main()
