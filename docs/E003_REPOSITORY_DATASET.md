# E003 — Repository-scale machine-labeled decisions

E001 only proved that the separated-candidate architecture could learn a tiny deterministic
task. E003 builds the first dataset path intended for meaningful held-out experiments.

## Why repository-wide candidates

A same-file classifier is too easy and does not resemble the eventual use case. E003 collects
top-level symbols across a repository and uses them as distractors for direct-call decisions.
Local symbols are preferred as hard negatives, then the remaining candidate budget is filled
from the repository-wide pool.

The target still comes from the Python AST. No LLM-generated labels are used.

## Leakage controls

Every example records its source file. Train/validation/test assignment is a stable hash of that
source path, so examples originating from one file cannot appear in multiple splits.

This is only a first barrier. For evaluation across cloned or highly repetitive repositories,
later experiments should also deduplicate structurally similar functions before splitting.

## Candidate-position controls

Candidate sets are deterministically shuffled from a seed plus example identity. The target is
therefore not tied to source order or a fixed answer slot.

## Build a dataset

~~~bash
python examples/build_repository_dataset.py /path/to/repo ./dataset \
  --max-candidates 16 \
  --seed 0
~~~

This writes:

~~~text
dataset/
  train.jsonl
  validation.jsonl
  test.jsonl
~~~

## Scope of E003

The current extractor resolves only direct calls to top-level functions in the same Python file;
repository-wide symbols are used as candidate distractors. Cross-file symbol resolution belongs
in the next supervision layer, where an LSP or static analyzer can provide ground truth.
