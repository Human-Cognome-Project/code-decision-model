"""E040 in-scope candidate pools: the retrieval stage, measured.

Every hard task so far hands the decision model a fixed number of candidates
(four in the frozen protocol) that the extractor chose to share the target's
AST call shape. That controls a shortcut, but it also hides the size of the
decision a local assistant really faces: for a masked direct call, the callee
must be a name in scope in the caller's file, and an assistant that may also
add an import faces every top-level function in the repository.

This module makes both pools explicit and deterministic, without a model:

- **scope pool**: module-level functions defined in the caller's file (the
  caller itself excluded) plus names imported by module-level
  ``from ... import ...`` statements that resolve, under the E030 resolver, to
  a top-level function elsewhere in the repository (aliases shadowed by a
  local definition excluded);
- **repository pool**: every top-level function in the repository other than
  the caller.

For each existing hard task the census reports the pool sizes, how many pool
members the E024 binding predicate leaves, how many share the target's call
shape (the extractor's own notion of a hard negative), and whether the target
is recovered at all, which it must be for the task to be well posed. That is
the retrieval side of OPEN_DIRECTIONS' two-stage path, measured separately
from ranking accuracy so a miss cannot hide inside decision accuracy.

``pool_example`` then re-poses any existing task over its bindable pool, so
the frozen scorer can be evaluated at pool scale by whoever runs it live;
nothing here trains or scores.
"""
from __future__ import annotations

import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .binding import CallSiteBindable
from .crossfile import _cross_file_imports
from .repository import PythonSymbol, _stable_rng, collect_python_symbols
from .synthetic import DecisionExample

DEFAULT_BODY_CHARS = 768
"""The hard extractors' default candidate body length; pool renderings must match it."""

LEVELS = ("scope", "repository")


def render_symbol(symbol: PythonSymbol, *, body_chars: int = DEFAULT_BODY_CHARS) -> str:
    """Render a symbol exactly as the hard extractors render a candidate."""
    return f"{symbol.signature}\n{symbol.body[:body_chars]}"


def caller_name(example: DecisionExample) -> str:
    """The masked caller's function name, read from the task context."""
    tree = ast.parse(example.context)
    node = tree.body[0] if tree.body else None
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError("task context does not start with a function definition")
    return node.name


@dataclass(frozen=True)
class InScopePool:
    """What a masked direct call in ``caller`` could legally name."""

    source: str
    caller: str
    local: tuple[PythonSymbol, ...]
    """Module-level functions in the caller's file, the caller excluded."""

    imported: tuple[PythonSymbol, ...]
    """From-imported top-level functions resolved elsewhere in the repository."""

    @property
    def symbols(self) -> tuple[PythonSymbol, ...]:
        seen: set[str] = set()
        result: list[PythonSymbol] = []
        for symbol in self.local + self.imported:
            if symbol.candidate not in seen:
                seen.add(symbol.candidate)
                result.append(symbol)
        return tuple(result)


@dataclass(frozen=True)
class RepositoryScope:
    """Scope pools for every module-level function in a repository."""

    pools: dict[tuple[str, str], InScopePool]
    """Keyed by (source file, caller name)."""

    all_symbols: tuple[PythonSymbol, ...]

    def pool_for(self, example: DecisionExample) -> InScopePool | None:
        return self.pools.get((example.source, caller_name(example)))

    def repository_pool(self, example: DecisionExample) -> tuple[PythonSymbol, ...]:
        """Every top-level function in the repository except the caller."""
        caller = caller_name(example)
        return tuple(
            symbol for symbol in self.all_symbols
            if not (symbol.source == example.source and symbol.name == caller)
        )

    def level_pool(self, example: DecisionExample, level: str) -> tuple[PythonSymbol, ...] | None:
        if level == "scope":
            pool = self.pool_for(example)
            return None if pool is None else pool.symbols
        if level == "repository":
            return self.repository_pool(example)
        raise ValueError(f"unknown pool level {level!r}")


def in_scope_pools(
    root: str | Path,
    *,
    source_roots: Sequence[str] = ("src",),
    strict: bool = False,
) -> RepositoryScope:
    """Build the scope pool of every module-level function in the repository.

    Uses the same symbol collection and the same conservative import resolver
    as the E006 and E030 extractors, so a task's target is in its scope pool by
    construction whenever the extractor could label it.
    """
    root_path = Path(root).resolve()
    roots = tuple(Path(r).as_posix() for r in source_roots)
    all_symbols, by_file = collect_python_symbols(root_path, strict=strict)
    known_files = frozenset(by_file)
    pools: dict[tuple[str, str], InScopePool] = {}

    for source_name, local_symbols in sorted(by_file.items()):
        try:
            tree = ast.parse((root_path / source_name).read_text(encoding="utf-8"), filename=source_name)
        except (OSError, UnicodeError, SyntaxError):
            if strict:
                raise
            continue
        local_names = {symbol.name for symbol in local_symbols}
        imports = _cross_file_imports(
            tree,
            known_files=known_files,
            importing_file=Path(source_name),
            by_file=by_file,
            source_roots=roots,
        )
        imported = tuple(
            symbol for alias, symbol in sorted(imports.items())
            if alias not in local_names
        )
        for caller in local_symbols:
            pools[(source_name, caller.name)] = InScopePool(
                source=source_name,
                caller=caller.name,
                local=tuple(symbol for symbol in local_symbols if symbol != caller),
                imported=imported,
            )
    return RepositoryScope(pools=pools, all_symbols=all_symbols)


# ---------------------------------------------------------------------------
# Predicate pruning and the census
# ---------------------------------------------------------------------------


def bindable_mask(
    example: DecisionExample,
    symbols: Sequence[PythonSymbol],
    *,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> tuple[bool, ...]:
    """E024 bindability of each pool symbol against the task's masked call."""
    if not symbols:
        return ()
    rendered = [render_symbol(symbol, body_chars=body_chars) for symbol in symbols]
    return tuple(CallSiteBindable().check(example.context, example.question, rendered).allowed)


def target_symbol(
    example: DecisionExample,
    symbols: Iterable[PythonSymbol],
    *,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> PythonSymbol | None:
    """The pool member whose rendering equals the task's labelled candidate."""
    wanted = example.candidates[example.answer_index]
    for symbol in symbols:
        if render_symbol(symbol, body_chars=body_chars) == wanted:
            return symbol
    return None


@dataclass(frozen=True)
class PoolCensus:
    """The retrieval stage for one task, at both pool levels."""

    protocol_candidates: int
    """Candidates the frozen task actually shows (four in the protocol)."""

    scope_size: int
    scope_local: int
    scope_imported: int
    scope_bindable: int
    scope_shape_matched: int
    """Scope members sharing the target's call shape (the extractor's negatives)."""

    target_in_scope: bool
    target_bindable_in_scope: bool

    repository_size: int
    repository_bindable: int
    target_in_repository: bool

    @property
    def scope_solved_by_predicate(self) -> bool:
        """Bindability alone leaves only the target in scope."""
        return self.target_bindable_in_scope and self.scope_bindable == 1


def pool_census(
    example: DecisionExample,
    scope: RepositoryScope,
    *,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> PoolCensus | None:
    """Census one task; None when its caller is not a module-level function."""
    pool = scope.pool_for(example)
    if pool is None:
        return None
    symbols = pool.symbols
    scope_mask = bindable_mask(example, symbols, body_chars=body_chars)
    target = target_symbol(example, symbols, body_chars=body_chars)
    target_bindable = bool(target is not None and scope_mask[symbols.index(target)])
    shape_matched = 0
    if target is not None:
        shape_matched = sum(symbol.call_shape == target.call_shape for symbol in symbols)

    repository = scope.repository_pool(example)
    repository_mask = bindable_mask(example, repository, body_chars=body_chars)
    return PoolCensus(
        protocol_candidates=len(example.candidates),
        scope_size=len(symbols),
        scope_local=len(pool.local),
        scope_imported=len(pool.imported),
        scope_bindable=sum(scope_mask),
        scope_shape_matched=shape_matched,
        target_in_scope=target is not None,
        target_bindable_in_scope=target_bindable,
        repository_size=len(repository),
        repository_bindable=sum(repository_mask),
        target_in_repository=target_symbol(example, repository, body_chars=body_chars) is not None,
    )


# ---------------------------------------------------------------------------
# Re-posing a task over its pool
# ---------------------------------------------------------------------------


def pool_example(
    example: DecisionExample,
    scope: RepositoryScope,
    *,
    level: str = "scope",
    candidate_count: int | None = None,
    seed: int = 0,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> DecisionExample | None:
    """The same task posed over its bindable pool at ``level``.

    With ``candidate_count`` None every bindable pool member is a candidate,
    which is the repository-scale decision itself. Otherwise the target plus
    ``candidate_count - 1`` bindable negatives are drawn by the same stable
    hash convention the hard extractors use. Candidate order is a stable
    shuffle. Returns None if the target is not a bindable member of the pool
    or the pool cannot fill the requested count.
    """
    if level not in LEVELS:
        raise ValueError(f"unknown pool level {level!r}")
    if candidate_count is not None and candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")
    symbols = scope.level_pool(example, level)
    if symbols is None:
        return None
    mask = bindable_mask(example, symbols, body_chars=body_chars)
    bindable = [symbol for symbol, ok in zip(symbols, mask) if ok]
    target = target_symbol(example, bindable, body_chars=body_chars)
    if target is None:
        return None

    rng = _stable_rng(seed, "in-scope-pool", level, example.source, caller_name(example), target.candidate)
    negatives = [symbol for symbol in bindable if symbol != target]
    if candidate_count is not None:
        if len(negatives) < candidate_count - 1:
            return None
        rng.shuffle(negatives)
        negatives = negatives[: candidate_count - 1]
    chosen = [target, *negatives]
    rng.shuffle(chosen)
    return DecisionExample(
        context=example.context,
        question=example.question,
        candidates=tuple(render_symbol(symbol, body_chars=body_chars) for symbol in chosen),
        answer_index=chosen.index(target),
        task=f"{example.task}.{level}_pool",
        source=example.source,
    )


def pool_examples(
    examples: Iterable[DecisionExample],
    scope: RepositoryScope,
    *,
    level: str = "scope",
    candidate_count: int | None = None,
    seed: int = 0,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> list[DecisionExample]:
    result = []
    for example in examples:
        widened = pool_example(
            example, scope, level=level, candidate_count=candidate_count, seed=seed, body_chars=body_chars
        )
        if widened is not None:
            result.append(widened)
    return result
