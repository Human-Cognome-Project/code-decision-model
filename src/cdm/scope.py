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

Both pools contain repository-defined top-level functions only. Builtins,
classes, names imported from outside the repository, and other module-level
callables are not included, so each pool is a lower bound on what the masked
call could legally name.

A candidate is identified by its rendered text, which is all a scorer sees.
Functions with identical renderings in different files are one candidate; a
task whose target shares its rendering with another pool member is ambiguous
at that level and is not re-posed.

For each existing hard task the census reports pool sizes in distinct
renderings, how many the E024 binding predicate leaves, how many share the
target's call shape, how many of the task's own protocol negatives are in the
caller's scope, and whether the target is in scope independently of the masked
call. A cross-file target is in scope through an import line; when no other
code in the file reads that alias, the import exists only because of the
masked call, which is the information E030 withholds from the scorer. Target
recovery is also reported, but it is a consistency check rather than a
finding: the extractors label from the same symbol collection and resolver,
so a miss means a bug, not a retrieval failure.

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


def distinct_by_rendering(
    symbols: Sequence[PythonSymbol],
    *,
    body_chars: int = DEFAULT_BODY_CHARS,
) -> tuple[tuple[PythonSymbol, ...], dict[str, int]]:
    """First symbol per distinct rendering, plus how many symbols share each rendering."""
    counts: dict[str, int] = {}
    kept: list[PythonSymbol] = []
    for symbol in symbols:
        text = render_symbol(symbol, body_chars=body_chars)
        counts[text] = counts.get(text, 0) + 1
        if counts[text] == 1:
            kept.append(symbol)
    return tuple(kept), counts


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

    imported_used_elsewhere: tuple[PythonSymbol, ...] = ()
    """Imported members whose alias is also read outside the caller, so the
    import would exist even if the caller's own call to it were not yet written."""

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
        aliases = {alias: symbol for alias, symbol in imports.items() if alias not in local_names}
        for caller in local_symbols:
            outside = _names_read_outside(tree, caller.name)
            pools[(source_name, caller.name)] = InScopePool(
                source=source_name,
                caller=caller.name,
                local=tuple(symbol for symbol in local_symbols if symbol != caller),
                imported=imported,
                imported_used_elsewhere=tuple(
                    symbol for alias, symbol in sorted(aliases.items()) if alias in outside
                ),
            )
    return RepositoryScope(pools=pools, all_symbols=all_symbols)


def _names_read_outside(tree: ast.Module, caller: str) -> frozenset[str]:
    """Names read by module-level statements other than the caller's definition and imports."""
    names: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and statement.name == caller:
            continue
        names.update(
            node.id for node in ast.walk(statement)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        )
    return frozenset(names)


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
    """The retrieval stage for one task, at both pool levels.

    Sizes count distinct candidate renderings, which is what a scorer sees.
    """

    protocol_candidates: int
    """Candidates the frozen task actually shows (four in the protocol)."""

    protocol_negatives_in_scope: int
    """How many of the task's own wrong candidates are in the caller's scope pool."""

    scope_size: int
    scope_local: int
    scope_imported: int
    """Local and imported member counts before rendering deduplication."""

    scope_bindable: int
    scope_shape_matched: int
    """Distinct scope renderings sharing the target's call shape (the extractor's negatives)."""

    target_in_scope: bool
    target_bindable_in_scope: bool
    target_unique_in_scope: bool
    """No other bindable scope member has the target's rendering."""

    target_in_scope_independently: bool
    """The target is in scope without the caller's own call: defined in the
    caller's file, or imported under an alias that is read outside the caller.
    For a cross-file target otherwise, scope membership rests on an import
    line that exists only because of the masked call."""

    repository_size: int
    repository_bindable: int
    target_in_repository: bool
    target_unique_in_repository: bool
    """No other bindable repository member has the target's rendering."""

    @property
    def scope_solved_by_predicate(self) -> bool:
        """Bindability alone leaves only the target in scope."""
        return self.target_bindable_in_scope and self.scope_bindable == 1

    @property
    def scope_filter_resolves_protocol(self) -> bool:
        """Dropping out-of-scope candidates from the frozen task leaves only the target."""
        return self.target_in_scope and self.protocol_negatives_in_scope == 0

    @property
    def scope_filter_resolves_protocol_independently(self) -> bool:
        """The scope filter resolves the task without relying on the target's own import."""
        return self.scope_filter_resolves_protocol and self.target_in_scope_independently


def _level_counts(
    example: DecisionExample,
    symbols: Sequence[PythonSymbol],
    *,
    body_chars: int,
) -> tuple[int, int, bool, bool, bool, tuple[PythonSymbol, ...]]:
    """(distinct size, distinct bindable, target present, target bindable, target unique, bindable distinct)."""
    distinct, _ = distinct_by_rendering(symbols, body_chars=body_chars)
    mask = bindable_mask(example, symbols, body_chars=body_chars)
    bindable = [symbol for symbol, ok in zip(symbols, mask) if ok]
    bindable_distinct, bindable_counts = distinct_by_rendering(bindable, body_chars=body_chars)
    wanted = example.candidates[example.answer_index]
    present = target_symbol(example, symbols, body_chars=body_chars) is not None
    count = bindable_counts.get(wanted, 0)
    return len(distinct), len(bindable_distinct), present, count >= 1, count == 1, bindable_distinct


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
    size, bindable, present, target_bindable, unique, _ = _level_counts(example, symbols, body_chars=body_chars)
    target = target_symbol(example, symbols, body_chars=body_chars)
    distinct, _ = distinct_by_rendering(symbols, body_chars=body_chars)
    shape_matched = 0 if target is None else sum(s.call_shape == target.call_shape for s in distinct)
    in_scope = {render_symbol(s, body_chars=body_chars) for s in symbols}
    negatives = [c for i, c in enumerate(example.candidates) if i != example.answer_index]

    repository = scope.repository_pool(example)
    r_size, r_bindable, r_present, _, r_unique, _ = _level_counts(example, repository, body_chars=body_chars)
    return PoolCensus(
        protocol_candidates=len(example.candidates),
        protocol_negatives_in_scope=sum(c in in_scope for c in negatives),
        scope_size=size,
        scope_local=len(pool.local),
        scope_imported=len(pool.imported),
        scope_bindable=bindable,
        scope_shape_matched=shape_matched,
        target_in_scope=present,
        target_bindable_in_scope=target_bindable,
        target_unique_in_scope=unique,
        target_in_scope_independently=target is not None and target.candidate in {
            symbol.candidate for symbol in pool.local + pool.imported_used_elsewhere
        },
        repository_size=r_size,
        repository_bindable=r_bindable,
        target_in_repository=r_present,
        target_unique_in_repository=r_unique,
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

    Candidates are distinct renderings. With ``candidate_count`` None every
    distinct bindable rendering is a candidate, which is the pool-scale
    decision itself. Otherwise the target plus ``candidate_count - 1``
    bindable negatives are drawn by the same stable hash convention the hard
    extractors use. Candidate order is a stable shuffle.

    Returns None when the target is not a bindable pool member, when another
    bindable member has the same rendering as the target (the label would be
    ambiguous), or when the pool cannot fill the requested count.
    """
    if level not in LEVELS:
        raise ValueError(f"unknown pool level {level!r}")
    if candidate_count is not None and candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")
    symbols = scope.level_pool(example, level)
    if symbols is None:
        return None
    _, _, _, target_bindable, unique, bindable = _level_counts(example, symbols, body_chars=body_chars)
    if not (target_bindable and unique):
        return None
    target = target_symbol(example, bindable, body_chars=body_chars)

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
