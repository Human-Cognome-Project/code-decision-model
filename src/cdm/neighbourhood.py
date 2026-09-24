"""E044 import-neighbourhood pools: a deterministic first stage for cross-file calls.

E042 showed that the frozen scorer keeps ranking signal over complete
repository pools, but that direct ranking of hundreds of candidates is not a
practical selection stage. E043 tests context-cosine retrieval as the bounded
first stage. This module measures a model-free alternative for E030 cross-file
calls: the functions defined in the repository files that the caller's file
already imports from.

The target's own import is the E030 label, so it must not reach the pool. The
file is read as it would be without that import, in two variants:

- **alias removed** (primary): every module-level name bound to the target is
  deleted from its import statement, and a statement left with no names is
  dropped. Other names imported from the same module remain, as they would in
  the file without the masked call.
- **independent** (strict): additionally, an imported name counts only if
  code outside the caller reads it, as in E040's independence measure, and
  star imports do not count. The file's other code then puts each remaining
  module in the neighbourhood, and nothing the masked caller alone depends on
  does.

A neighbourhood file is any repository file, other than the caller's own, that
a remaining module-level import resolves to under the E030 conservative
resolver: the module of a ``from ... import ...`` statement, a submodule named
by one of its names, or the module of an ``import a.b`` statement.

The pool is every top-level function defined in a neighbourhood file,
rendered, deduplicated by rendering and pruned by the unchanged E024 binding
predicate exactly as in E040. The census reports whether the target survives,
how large the pool is, and the recall a uniform random subset of the bindable
repository pool of the same size would have. Nothing here trains, scores, or
calls a model.
"""
from __future__ import annotations

import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .crossfile import _cross_file_imports, _module_file
from .repository import PythonSymbol, collect_python_symbols
from .scope import (
    DEFAULT_BODY_CHARS,
    _names_read_outside,
    bindable_mask,
    caller_name,
    distinct_by_rendering,
    render_symbol,
)
from .synthetic import DecisionExample

VARIANTS = ("alias", "independent")


@dataclass(frozen=True)
class RepositoryNeighbourhoods:
    """Parsed module-level imports and symbols for one repository."""

    root: Path
    source_roots: tuple[str, ...]
    all_symbols: tuple[PythonSymbol, ...]
    by_file: dict[str, tuple[PythonSymbol, ...]]
    trees: dict[str, ast.Module]

    @property
    def known_files(self) -> frozenset[str]:
        return frozenset(self.by_file)

    def target_aliases(
        self, example: DecisionExample, *, body_chars: int = DEFAULT_BODY_CHARS
    ) -> frozenset[str]:
        """Module-level names in the caller's file that resolve to the labelled target."""
        tree = self.trees.get(example.source)
        if tree is None:
            return frozenset()
        wanted = example.candidates[example.answer_index]
        imports = _cross_file_imports(
            tree,
            known_files=self.known_files,
            importing_file=Path(example.source),
            by_file=self.by_file,
            source_roots=self.source_roots,
        )
        return frozenset(
            alias for alias, symbol in imports.items()
            if render_symbol(symbol, body_chars=body_chars) == wanted
        )

    def neighbourhood_files(
        self,
        example: DecisionExample,
        *,
        variant: str = "alias",
        body_chars: int = DEFAULT_BODY_CHARS,
    ) -> tuple[str, ...] | None:
        """Repository files the caller's file imports from, without the target's import.

        None when the caller's file is unparsed or no module-level name binds the
        target, which would mean the task was not an E030 cross-file task.
        """
        if variant not in VARIANTS:
            raise ValueError(f"unknown neighbourhood variant {variant!r}")
        tree = self.trees.get(example.source)
        aliases = self.target_aliases(example, body_chars=body_chars)
        if tree is None or not aliases:
            return None
        importing = Path(example.source)
        files: list[str] = []
        read_outside = _names_read_outside(tree, caller_name(example)) if variant == "independent" else None

        def keep(bound: str) -> bool:
            if bound in aliases:
                return False
            return read_outside is None or bound in read_outside

        def add(module: str | None, level: int) -> None:
            resolved = _module_file(
                self.known_files, importing, module, level, source_roots=self.source_roots
            )
            if resolved is not None and resolved != example.source and resolved not in files:
                files.append(resolved)

        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom):
                kept = [
                    alias for alias in statement.names
                    if alias.name != "*" and keep(alias.asname or alias.name)
                ]
                # A star import brings the module in, but which names are read
                # cannot be told, so it counts only in the primary variant.
                star = variant == "alias" and any(alias.name == "*" for alias in statement.names)
                if not kept and not star:
                    continue
                add(statement.module, statement.level)
                for alias in kept:
                    submodule = f"{statement.module}.{alias.name}" if statement.module else alias.name
                    add(submodule, statement.level)
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    if keep(alias.asname or alias.name.split(".")[0]):
                        add(alias.name, 0)
        return tuple(files)

    def neighbourhood_pool(
        self,
        example: DecisionExample,
        *,
        variant: str = "alias",
        body_chars: int = DEFAULT_BODY_CHARS,
    ) -> tuple[PythonSymbol, ...] | None:
        """Every top-level function in the neighbourhood files."""
        files = self.neighbourhood_files(example, variant=variant, body_chars=body_chars)
        if files is None:
            return None
        return tuple(symbol for name in files for symbol in self.by_file.get(name, ()))

    def repository_pool(self, example: DecisionExample) -> tuple[PythonSymbol, ...]:
        """Every top-level function in the repository except the caller."""
        caller = caller_name(example)
        return tuple(
            symbol for symbol in self.all_symbols
            if not (symbol.source == example.source and symbol.name == caller)
        )


def import_neighbourhoods(
    root: str | Path,
    *,
    source_roots: Sequence[str] = ("src",),
    strict: bool = False,
) -> RepositoryNeighbourhoods:
    """Parse every repository file once, with the same symbol collection as E006/E030."""
    root_path = Path(root).resolve()
    all_symbols, by_file = collect_python_symbols(root_path, strict=strict)
    trees: dict[str, ast.Module] = {}
    for name in by_file:
        try:
            trees[name] = ast.parse((root_path / name).read_text(encoding="utf-8"), filename=name)
        except (OSError, UnicodeError, SyntaxError):
            if strict:
                raise
    return RepositoryNeighbourhoods(
        root=root_path,
        source_roots=tuple(Path(r).as_posix() for r in source_roots),
        all_symbols=all_symbols,
        by_file=by_file,
        trees=trees,
    )


def _bindable_distinct(
    example: DecisionExample, symbols: Sequence[PythonSymbol], *, body_chars: int
) -> dict[str, int]:
    """Distinct bindable renderings and how many symbols share each."""
    mask = bindable_mask(example, symbols, body_chars=body_chars)
    bindable = [symbol for symbol, ok in zip(symbols, mask) if ok]
    _, counts = distinct_by_rendering(bindable, body_chars=body_chars)
    return counts


@dataclass(frozen=True)
class NeighbourhoodCensus:
    """The import-neighbourhood first stage for one cross-file task."""

    repository_bindable: int
    """Distinct E024-bindable renderings in the repository pool."""

    target_unique_in_repository: bool
    """No other bindable repository function renders like the target."""

    alias_files: int
    alias_bindable: int
    target_in_alias_pool: bool

    independent_files: int
    independent_bindable: int
    target_in_independent_pool: bool

    @property
    def alias_uniform_recall(self) -> float:
        """Recall of a uniform random bindable subset of the alias pool's size."""
        if not self.repository_bindable:
            return 0.0
        return min(self.alias_bindable, self.repository_bindable) / self.repository_bindable

    @property
    def independent_uniform_recall(self) -> float:
        if not self.repository_bindable:
            return 0.0
        return min(self.independent_bindable, self.repository_bindable) / self.repository_bindable


def neighbourhood_census(
    example: DecisionExample,
    neighbourhoods: RepositoryNeighbourhoods,
    *,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> NeighbourhoodCensus | None:
    """Census one E030 task; None when no module-level name binds its target."""
    wanted = example.candidates[example.answer_index]
    repository = _bindable_distinct(example, neighbourhoods.repository_pool(example), body_chars=body_chars)
    levels = {}
    for variant in VARIANTS:
        files = neighbourhoods.neighbourhood_files(example, variant=variant, body_chars=body_chars)
        if files is None:
            return None
        pool = neighbourhoods.neighbourhood_pool(example, variant=variant, body_chars=body_chars)
        counts = _bindable_distinct(example, pool, body_chars=body_chars)
        levels[variant] = (len(files), len(counts), wanted in counts)
    return NeighbourhoodCensus(
        repository_bindable=len(repository),
        target_unique_in_repository=repository.get(wanted, 0) == 1,
        alias_files=levels["alias"][0],
        alias_bindable=levels["alias"][1],
        target_in_alias_pool=levels["alias"][2],
        independent_files=levels["independent"][0],
        independent_bindable=levels["independent"][1],
        target_in_independent_pool=levels["independent"][2],
    )


def neighbourhood_censuses(
    examples: Iterable[DecisionExample],
    neighbourhoods: RepositoryNeighbourhoods,
    *,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> list[NeighbourhoodCensus | None]:
    return [neighbourhood_census(e, neighbourhoods, body_chars=body_chars) for e in examples]
