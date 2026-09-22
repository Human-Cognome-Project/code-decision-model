"""Repository-scale machine-labeled decision extraction.

The extractor intentionally begins with facts Python's AST can verify exactly. It does
not ask a language model to label training data.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from itertools import permutations
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
    positional_arity: int
    required_positional: int
    keyword_only_arity: int
    required_keyword_only: int
    has_vararg: bool
    has_kwarg: bool
    is_async: bool

    @property
    def candidate(self) -> str:
        return f"{self.source}::{self.signature}"

    @property
    def call_shape(self) -> tuple[int, int, int, int, bool, bool, bool]:
        """Structural function shape used to control easy candidate shortcuts."""
        return (
            self.positional_arity,
            self.required_positional,
            self.keyword_only_arity,
            self.required_keyword_only,
            self.has_vararg,
            self.has_kwarg,
            self.is_async,
        )


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
    """Render parameter names while preserving Python's parameter categories."""
    parts: list[str] = []

    if node.args.posonlyargs:
        parts.extend(arg.arg for arg in node.args.posonlyargs)
        parts.append("/")

    parts.extend(arg.arg for arg in node.args.args)

    if node.args.vararg is not None:
        parts.append("*" + node.args.vararg.arg)
    elif node.args.kwonlyargs:
        parts.append("*")

    parts.extend(arg.arg for arg in node.args.kwonlyargs)

    if node.args.kwarg is not None:
        parts.append("**" + node.args.kwarg.arg)

    return f"{node.name}({', '.join(parts)})"


def _call_shape(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[int, int, int, int, bool, bool, bool]:
    """Return structural parameter counts/requirements and async/variadic flags."""
    positional = len(node.args.posonlyargs) + len(node.args.args)
    required_positional = positional - len(node.args.defaults)
    keyword_only = len(node.args.kwonlyargs)
    required_keyword_only = sum(
        default is None for default in node.args.kw_defaults
    )
    return (
        positional,
        required_positional,
        keyword_only,
        required_keyword_only,
        node.args.vararg is not None,
        node.args.kwarg is not None,
        isinstance(node, ast.AsyncFunctionDef),
    )


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
            (
                positional,
                required_positional,
                keyword_only,
                required_keyword_only,
                has_vararg,
                has_kwarg,
                is_async,
            ) = _call_shape(node)
            symbols.append(
                PythonSymbol(
                    source=rel.as_posix(),
                    name=node.name,
                    signature=_signature(node),
                    body=body,
                    positional_arity=positional,
                    required_positional=required_positional,
                    keyword_only_arity=keyword_only,
                    required_keyword_only=required_keyword_only,
                    has_vararg=has_vararg,
                    has_kwarg=has_kwarg,
                    is_async=is_async,
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


class _DirectCallVisitor(ast.NodeVisitor):
    """Collect calls executed in one function body without entering nested scopes."""

    def __init__(
        self,
        root: ast.FunctionDef | ast.AsyncFunctionDef,
        local_names: set[str],
    ) -> None:
        self.root = root
        self.local_names = local_names
        self.targets: list[str] = []

    def _visit_root_body(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node is self.root:
            for statement in node.body:
                self.visit(statement)
        # Nested function bodies are intentionally separate scopes.

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_root_body(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_root_body(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # A lambda body executes only when the lambda is invoked, not when defined.
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Conservatively exclude calls inside a nested class body from the function label.
        return

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Name)
            and node.func.id in self.local_names
            and node.func.id != self.root.name
        ):
            self.targets.append(node.func.id)
        self.generic_visit(node)


def _direct_local_target_names(source: str, symbols: tuple[PythonSymbol, ...]) -> dict[str, str]:
    """Return caller->callee for callers with exactly one direct local target."""
    tree = ast.parse(source)
    local_names = {symbol.name for symbol in symbols}
    result: dict[str, str] = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        visitor = _DirectCallVisitor(node, local_names)
        visitor.visit(node)
        unique = tuple(dict.fromkeys(visitor.targets))
        if len(unique) == 1:
            result[node.name] = unique[0]

    return result


def _candidate_symbols(
    *,
    target: PythonSymbol,
    local_symbols: tuple[PythonSymbol, ...],
    all_symbols: tuple[PythonSymbol, ...],
    max_candidates: int,
    seed: int,
    key: str,
) -> tuple[tuple[PythonSymbol, ...], int]:
    """Choose deterministic repository-wide candidate symbols containing the target."""
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
    frozen = tuple(chosen)
    return frozen, frozen.index(target)


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
    symbols, answer_index = _candidate_symbols(
        target=target,
        local_symbols=local_symbols,
        all_symbols=all_symbols,
        max_candidates=max_candidates,
        seed=seed,
        key=key,
    )
    return tuple(symbol.candidate for symbol in symbols), answer_index


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


class _TargetNameMasker(ast.NodeTransformer):
    """Replace references to one symbol with a neutral call-target marker."""

    def __init__(self, target_name: str) -> None:
        self.target_name = target_name

    def visit_Name(self, node: ast.Name):
        if node.id == self.target_name:
            return ast.copy_location(
                ast.Name(id="__CALL_TARGET__", ctx=node.ctx),
                node,
            )
        return node


def _masked_function_body(
    source: str,
    *,
    caller_name: str,
    target_name: str,
) -> str | None:
    """Return a normalized caller definition with target-name references removed."""
    tree = ast.parse(source)
    caller = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == caller_name
        ),
        None,
    )
    if caller is None:
        return None

    masked = copy.deepcopy(caller)
    masked = _TargetNameMasker(target_name).visit(masked)
    ast.fix_missing_locations(masked)

    # The target should no longer survive as an executable Name node.
    if any(
        isinstance(node, ast.Name) and node.id == target_name
        for node in ast.walk(masked)
    ):
        return None

    rendered = ast.unparse(masked)

    # Be stricter than AST identity alone: reject any example where the exact target
    # identifier survives in a string literal, annotation, nested definition name,
    # attribute, or other textual artifact that could restore trivial name matching.
    if re.search(rf"\b{re.escape(target_name)}\b", rendered):
        return None
    return rendered


def _rich_candidate(symbol: PythonSymbol, *, body_chars: int) -> str:
    """Render a candidate with enough implementation context for semantic matching."""
    body = symbol.body
    if body_chars > 0:
        body = body[:body_chars]
    return f"{symbol.candidate}\n{body}"


def repository_masked_call_examples(
    root: str | Path,
    *,
    max_candidates: int = 16,
    candidate_body_chars: int = 768,
    seed: int = 0,
    strict: bool = False,
) -> list[DecisionExample]:
    """Create call-target decisions after removing the target identifier from the caller.

    The ground-truth edge still comes directly from the AST, but the caller no longer
    contains the callee identifier as an executable Name. Candidate definitions include
    source, signature, and a bounded body excerpt so string equality alone cannot solve
    the task.
    """
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
            masked_body = _masked_function_body(
                source_text,
                caller_name=caller_name,
                target_name=target_name,
            )
            if masked_body is None:
                continue

            symbols, answer_index = _candidate_symbols(
                target=target,
                local_symbols=local_symbols,
                all_symbols=all_symbols,
                max_candidates=min(max_candidates, len(all_symbols)),
                seed=seed,
                key=f"masked:{source_name}:{caller_name}",
            )
            candidates = tuple(
                _rich_candidate(symbol, body_chars=candidate_body_chars)
                for symbol in symbols
            )
            context = f"file: {source_name}\n\n{masked_body}"
            examples.append(
                DecisionExample(
                    context=context,
                    question=(
                        "Which candidate definition should replace "
                        "__CALL_TARGET__ in this caller?"
                    ),
                    candidates=candidates,
                    answer_index=answer_index,
                    task="python.masked_direct_call",
                    source=source_name,
                )
            )

    return examples


def repository_hard_masked_call_examples(
    root: str | Path,
    *,
    candidate_count: int = 4,
    candidate_body_chars: int = 768,
    seed: int = 0,
    strict: bool = False,
) -> list[DecisionExample]:
    """Create a harder masked-call task with structural shortcuts controlled.

    Every candidate:
    - comes from the caller's source file;
    - has the same AST-derived structural call shape as the true target;
    - is not the caller itself.

    File paths are omitted from both context and candidate text because they carry no
    useful semantic information once the pool is local. Examples that cannot provide
    the full fixed candidate count are skipped.
    """
    if candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")

    root_path = Path(root).resolve()
    _, by_file = collect_python_symbols(root_path, strict=strict)
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
            masked_body = _masked_function_body(
                source_text,
                caller_name=caller_name,
                target_name=target_name,
            )
            if masked_body is None:
                continue

            pool = [
                symbol
                for symbol in local_symbols
                if symbol != caller
                and symbol.call_shape == target.call_shape
            ]
            if target not in pool or len(pool) < candidate_count:
                continue

            rng = _stable_rng(
                seed,
                "hard-masked",
                source_name,
                caller_name,
                target.candidate,
            )
            negatives = [symbol for symbol in pool if symbol != target]
            rng.shuffle(negatives)
            chosen = [target, *negatives[: candidate_count - 1]]
            rng.shuffle(chosen)

            candidates = tuple(
                f"{symbol.signature}\n{symbol.body[:candidate_body_chars]}"
                for symbol in chosen
            )
            answer_index = chosen.index(target)

            examples.append(
                DecisionExample(
                    context=masked_body,
                    question=(
                        "Which candidate definition should replace "
                        "__CALL_TARGET__ in this caller?"
                    ),
                    candidates=candidates,
                    answer_index=answer_index,
                    task="python.hard_masked_direct_call",
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


def namespace_repository_examples(
    examples: Iterable[DecisionExample],
    namespace: str,
) -> tuple[DecisionExample, ...]:
    """Prefix source provenance so examples from multiple repositories can be pooled."""
    if not namespace or "::" in namespace:
        raise ValueError("namespace must be non-empty and cannot contain '::'")

    result: list[DecisionExample] = []
    for example in examples:
        if example.source is None:
            raise ValueError("repository examples require source provenance")
        result.append(
            replace(
                example,
                source=f"{namespace}::{example.source}",
            )
        )
    return tuple(result)


def split_repository_examples_balanced(
    examples: Iterable[DecisionExample],
    *,
    seed: int = 0,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
) -> RepositoryDataset:
    """Create deterministic, source-disjoint splits balanced by example count.

    The older hash splitter independently maps each source into a probability range.
    That is useful for stable assignment, but small repositories can accidentally
    receive no validation or test examples. This splitter treats each source file as
    an indivisible group and greedily minimizes deviation from requested example
    counts while preserving source-file isolation.

    When validation_fraction is nonzero, at least three source groups are required.
    """
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0.0 <= validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1")
    test_fraction = 1.0 - train_fraction - validation_fraction
    if test_fraction <= 0.0:
        raise ValueError("train + validation fractions must leave room for test")

    materialized = tuple(examples)
    if not materialized:
        return RepositoryDataset(train=(), validation=(), test=())

    groups: dict[str, list[DecisionExample]] = {}
    for example in materialized:
        if example.source is None:
            raise ValueError("repository examples require source provenance")
        groups.setdefault(example.source, []).append(example)

    fractions = {
        "train": train_fraction,
        "validation": validation_fraction,
        "test": test_fraction,
    }
    active = tuple(name for name, fraction in fractions.items() if fraction > 0.0)
    if len(groups) < len(active):
        raise ValueError(
            f"need at least {len(active)} source groups for non-empty requested splits"
        )

    total = len(materialized)
    targets = {name: total * fractions[name] for name in active}

    def stable_key(source: str) -> int:
        digest = hashlib.sha256(f"{seed}:{source}".encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: (-len(item[1]), stable_key(item[0]), item[0]),
    )

    assigned: dict[str, list[tuple[str, list[DecisionExample]]]] = {
        name: [] for name in active
    }
    counts = {name: 0 for name in active}

    def cost(proposed: dict[str, int]) -> float:
        return sum(
            ((proposed[name] - targets[name]) / max(targets[name], 1.0)) ** 2
            for name in active
        )

    # Seed each requested split with one of the largest groups. Try every mapping so
    # the non-empty guarantee introduces the smallest possible imbalance.
    seed_groups = ordered_groups[: len(active)]
    best_perm = min(
        permutations(active),
        key=lambda perm: cost({
            name: sum(
                len(group)
                for (_, group), assigned_name in zip(seed_groups, perm)
                if assigned_name == name
            )
            for name in active
        }),
    )
    for (source, group), split_name in zip(seed_groups, best_perm):
        assigned[split_name].append((source, group))
        counts[split_name] += len(group)

    # Largest-first bin packing keeps one unusually large source from becoming a
    # late surprise. Relative squared error prevents the train target from dominating
    # the much smaller validation/test targets.
    for source, group in ordered_groups[len(active):]:
        size = len(group)

        def placement_cost(split_name: str) -> tuple[float, int]:
            proposed = dict(counts)
            proposed[split_name] += size
            return cost(proposed), active.index(split_name)

        split_name = min(active, key=placement_cost)
        assigned[split_name].append((source, group))
        counts[split_name] += size

    def flatten(name: str) -> tuple[DecisionExample, ...]:
        if name not in assigned:
            return ()
        return tuple(
            example
            for _, group in assigned[name]
            for example in group
        )

    return RepositoryDataset(
        train=flatten("train"),
        validation=flatten("validation"),
        test=flatten("test"),
    )


def split_repository_examples_by_namespace(
    examples: Iterable[DecisionExample],
    *,
    seed: int = 0,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
    small_namespace: str = "train",
) -> RepositoryDataset:
    """Balance source-disjoint splits independently inside each repository namespace.

    Sources must have been prefixed with namespace_repository_examples. Namespaces
    with too few source groups to populate every requested partition can either be
    placed entirely in training (small_namespace="train") or rejected
    (small_namespace="error").
    """
    if small_namespace not in {"train", "error"}:
        raise ValueError("small_namespace must be 'train' or 'error'")

    materialized = tuple(examples)
    if not materialized:
        return RepositoryDataset(train=(), validation=(), test=())

    strata: dict[str, list[DecisionExample]] = {}
    for example in materialized:
        if example.source is None or "::" not in example.source:
            raise ValueError(
                "namespace-stratified splitting requires namespaced source provenance"
            )
        namespace, _ = example.source.split("::", 1)
        strata.setdefault(namespace, []).append(example)

    requested_splits = 2 + int(validation_fraction > 0.0)
    combined = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for namespace in sorted(strata):
        stratum = strata[namespace]
        source_count = len({example.source for example in stratum})
        if source_count < requested_splits:
            if small_namespace == "error":
                raise ValueError(
                    f"namespace {namespace!r} has {source_count} source groups; "
                    f"need {requested_splits}"
                )
            combined["train"].extend(stratum)
            continue

        split = split_repository_examples_balanced(
            stratum,
            seed=seed,
            train_fraction=train_fraction,
            validation_fraction=validation_fraction,
        )
        combined["train"].extend(split.train)
        combined["validation"].extend(split.validation)
        combined["test"].extend(split.test)

    return RepositoryDataset(
        train=tuple(combined["train"]),
        validation=tuple(combined["validation"]),
        test=tuple(combined["test"]),
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
