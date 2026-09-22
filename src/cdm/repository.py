"""Repository-scale machine-labeled decision extraction.

The extractor intentionally begins with facts Python's AST can verify exactly. It does
not ask a language model to label training data.
"""
from __future__ import annotations

import ast
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .synthetic import DecisionExample

DEFAULT_EXCLUDED_DIRS = frozenset({
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
})


@dataclass(frozen=True)
class PythonSymbol:
    """A repository-qualified top-level Python function."""

    source: str
    name: str
    signature: str
    body: str

    @property
    def candidate(self) -> str:
        return f"{self.source}::{self.signature}"


@dataclass(frozen=True)
class RepositoryDataset:
    """File-disjoint dataset partitions."""

    train: tuple[DecisionExample, ...]
    validation: tuple[DecisionExample, ...]
    test: tuple[DecisionExample, ...]

    def sizes(self) -> dict[str, int]:
        return {
            "train": len(self.train),
            "validation": len(self.validation),
            "test": len(self.test),
        }


def iter_python_files(
    root: str | Path,
    *,
    excluded_dirs: Iterable[str] = DEFAULT_EXCLUDED_DIRS,
) -> list[Path]:
    """Return repository-relative Python source files in deterministic order."""
    root_path = Path(root).resolve()
    excluded = set(excluded_dirs)
    files: list[Path] = []

    for path in root_path.rglob("*.py"):
        try:
            rel = path.relative_to(root_path)
        except ValueError:
            continue
        if any(part in excluded for part in rel.parts[:-1]):
            continue
        if path.is_file():
            files.append(rel)

    return sorted(files, key=lambda p: p.as_posix())


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [arg.arg for arg in node.args.args]
    if node.args.vararg is not None:
        args.append("*" + node.args.vararg.arg)
    if node.args.kwarg is not None:
        args.append("**" + node.args.kwarg.arg)
    return f"{node.name}({', '.join(args)})"


def _parse_file(root: Path, rel: Path, *, strict: bool) -> tuple[list[PythonSymbol], ast.Module] | None:
    path = root / rel
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel.as_posix())
    except (OSError, UnicodeError, SyntaxError):
        if strict:
            raise
        return None

    symbols: list[PythonSymbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = ast.get_source_segment(source, node) or node.name
            symbols.append(
                PythonSymbol(
                    source=rel.as_posix(),
                    name=node.name,
                    signature=_signature(node),
                    body=body,
                )
            )
    return symbols, tree


def collect_python_symbols(
    root: str | Path,
    *,
    strict: bool = False,
) -> tuple[tuple[PythonSymbol, ...], dict[str, tuple[PythonSymbol, ...]]]:
    """Collect top-level Python functions and group them by source file."""
    root_path = Path(root).resolve()
    all_symbols: list[PythonSymbol] = []
    by_file: dict[str, tuple[PythonSymbol, ...]] = {}

    for rel in iter_python_files(root_path):
        parsed = _parse_file(root_path, rel, strict=strict)
        if parsed is None:
            continue
        symbols, _ = parsed
        if not symbols:
            continue
        frozen = tuple(symbols)
        by_file[rel.as_posix()] = frozen
        all_symbols.extend(frozen)

    return tuple(all_symbols), by_file


def _stable_rng(*parts: object) -> random.Random:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return random.Random(seed)


def _direct_local_target_names(source: str, symbols: tuple[PythonSymbol, ...]) -> dict[str, str]:
    """Return caller->callee for callers with exactly one distinct local target."""
    tree = ast.parse(source)
    local_names = {symbol.name for symbol in symbols}
    result: dict[str, str] = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        targets: list[str] = []
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id in local_names
                and child.func.id != node.name
            ):
                targets.append(child.func.id)
        unique = tuple(dict.fromkeys(targets))
        if len(unique) == 1:
            result[node.name] = unique[0]

    return result


def _candidate_set(
    *,
    target: PythonSymbol,
    local_symbols: tuple[PythonSymbol, ...],
    all_symbols: tuple[PythonSymbol, ...],
    max_candidates: int,
    seed: int,
    key: str,
) -> tuple[tuple[str, ...], int]:
    """Build a deterministic repository-wide candidate set containing the target."""
    if max_candidates < 2:
        raise ValueError("max_candidates must be at least 2")

    rng = _stable_rng(seed, key, target.candidate)
    chosen: list[PythonSymbol] = [target]

    # Local symbols are intentionally preferred as harder negatives.
    local_negatives = [symbol for symbol in local_symbols if symbol != target]
    rng.shuffle(local_negatives)
    chosen.extend(local_negatives[: max_candidates - 1])

    if len(chosen) < max_candidates:
        chosen_candidates = {symbol.candidate for symbol in chosen}
        global_negatives = [
            symbol
            for symbol in all_symbols
            if symbol.candidate not in chosen_candidates
        ]
        rng.shuffle(global_negatives)
        chosen.extend(global_negatives[: max_candidates - len(chosen)])

    rng.shuffle(chosen)
    candidates = tuple(symbol.candidate for symbol in chosen)
    return candidates, candidates.index(target.candidate)


def repository_call_examples(
    root: str | Path,
    *,
    max_candidates: int = 16,
    seed: int = 0,
    strict: bool = False,
) -> list[DecisionExample]:
    """Create repository-wide direct-call decisions with deterministic hard negatives."""
    root_path = Path(root).resolve()
    all_symbols, by_file = collect_python_symbols(root_path, strict=strict)
    if len(all_symbols) < 2:
        return []

    examples: list[DecisionExample] = []
    for source_name, local_symbols in sorted(by_file.items()):
        path = root_path / source_name
        try:
            source_text = path.read_text(encoding="utf-8")
            targets = _direct_local_target_names(source_text, local_symbols)
        except (OSError, UnicodeError, SyntaxError):
            if strict:
                raise
            continue

        by_name = {symbol.name: symbol for symbol in local_symbols}
        for caller_name, target_name in sorted(targets.items()):
            caller = by_name[caller_name]
            target = by_name[target_name]
            candidates, answer_index = _candidate_set(
                target=target,
                local_symbols=local_symbols,
                all_symbols=all_symbols,
                max_candidates=min(max_candidates, len(all_symbols)),
                seed=seed,
                key=f"{source_name}:{caller_name}",
            )
            context = f"file: {source_name}\n\n{caller.body}"
            examples.append(
                DecisionExample(
                    context=context,
                    question=(
                        f"Which repository symbol is directly called by "
                        f"{source_name}::{caller.signature}?"
                    ),
                    candidates=candidates,
                    answer_index=answer_index,
                    task="python.direct_call",
                    source=source_name,
                )
            )

    return examples


def split_for_source(
    source: str,
    *,
    seed: int = 0,
    train_fraction: float = 0.8,
    validation_fraction: float = 0.1,
) -> str:
    """Assign an entire source file to a stable split."""
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0.0 <= validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1.0:
        raise ValueError("train + validation fractions must leave room for test")

    digest = hashlib.sha256(f"{seed}:{source}".encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") / 2**64
    if value < train_fraction:
        return "train"
    if value < train_fraction + validation_fraction:
        return "validation"
    return "test"


def split_repository_examples(
    examples: Iterable[DecisionExample],
    *,
    seed: int = 0,
    train_fraction: float = 0.8,
    validation_fraction: float = 0.1,
) -> RepositoryDataset:
    """Split by source file so examples from one file never cross partitions."""
    buckets: dict[str, list[DecisionExample]] = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for example in examples:
        if example.source is None:
            raise ValueError("repository examples require source provenance")
        split = split_for_source(
            example.source,
            seed=seed,
            train_fraction=train_fraction,
            validation_fraction=validation_fraction,
        )
        buckets[split].append(example)

    return RepositoryDataset(
        train=tuple(buckets["train"]),
        validation=tuple(buckets["validation"]),
        test=tuple(buckets["test"]),
    )


def write_jsonl_dataset(dataset: RepositoryDataset, output_dir: str | Path) -> dict[str, Path]:
    """Write train/validation/test JSONL files and return their paths."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    for split, examples in (
        ("train", dataset.train),
        ("validation", dataset.validation),
        ("test", dataset.test),
    ):
        path = out / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for example in examples:
                row = asdict(example)
                row["candidates"] = list(example.candidates)
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        paths[split] = path

    return paths
