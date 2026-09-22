"""Machine-verified cross-file call supervision (E030).

Every existing hard task resolves a masked call inside one file. This module
adds the first cross-file decision with the same integrity controls. The label
comes from deterministic import resolution: a module-level

    from package.module import name

statement in the caller's file, resolved to a top-level function definition in
another file of the same repository. No language server and no model is
consulted; an import that cannot be resolved inside the repository is ignored.
"""
from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from pathlib import Path

from .repository import (
    PythonSymbol,
    _DirectCallVisitor,
    _masked_function_body,
    _stable_rng,
    collect_python_symbols,
)
from .synthetic import DecisionExample

TASK = "python.hard_masked_cross_file_call"


def _module_file(
    known_files: frozenset[str],
    importing_file: Path,
    module: str | None,
    level: int,
    *,
    source_roots: tuple[str, ...],
) -> str | None:
    """Resolve an import statement to a repository-relative Python file.

    Absolute imports are accepted only when exactly one file matches the module
    path under the supported roots: the repository root and each declared
    source root (``src`` by default). There is no implicit-relative fallback
    through the importing file's ancestors, because Python 3 does not resolve
    absolute imports that way. A module path that matches more than one file,
    across roots or as both ``name.py`` and ``name/__init__.py``, is ambiguous
    and skipped. Relative imports follow the usual package rules. Anything
    that does not resolve to a parsed repository file returns None.
    """
    parts = tuple(module.split(".")) if module else ()

    if level == 0:
        if not parts:
            return None
        bases = [Path("."), *(Path(root) for root in source_roots)]
    else:
        base = importing_file.parent
        for _ in range(level - 1):
            base = base.parent
        bases = [base]

    matches: list[str] = []
    for base in bases:
        target = base.joinpath(*parts) if parts else base
        for candidate in (target.with_suffix(".py"), target / "__init__.py"):
            rel = candidate.as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            if rel in known_files and rel not in matches:
                matches.append(rel)

    if len(matches) != 1:
        return None
    return matches[0]


def _cross_file_imports(
    tree: ast.Module,
    *,
    known_files: frozenset[str],
    importing_file: Path,
    by_file: dict[str, tuple[PythonSymbol, ...]],
    source_roots: tuple[str, ...],
) -> dict[str, PythonSymbol]:
    """Map local alias -> imported top-level function defined in another file.

    Only direct module-level ``from ... import ...`` statements count. Names that
    are not unique top-level functions in the resolved file are ignored.
    """
    importing_rel = importing_file.as_posix()
    result: dict[str, PythonSymbol] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        target_file = _module_file(
            known_files,
            importing_file,
            statement.module,
            statement.level,
            source_roots=source_roots,
        )
        if target_file is None or target_file == importing_rel:
            continue
        symbols = by_file.get(target_file, ())
        for alias in statement.names:
            if alias.name == "*":
                continue
            matches = [symbol for symbol in symbols if symbol.name == alias.name]
            if len(matches) != 1:
                continue
            result[alias.asname or alias.name] = matches[0]
    return result


def repository_hard_masked_cross_file_call_examples(
    root: str | Path,
    *,
    candidate_count: int = 4,
    candidate_body_chars: int = 768,
    seed: int = 0,
    strict: bool = False,
    source_roots: Sequence[str] = ("src",),
) -> list[DecisionExample]:
    """Create cross-file call decisions with import-resolved exact labels.

    A top-level function becomes a caller when its body directly calls exactly
    one distinct imported name that resolves to a top-level function in another
    repository file. The alias is masked in the caller; the import statement is
    not part of the context.

    Integrity controls, matching E006/E008/E015:
    - nested function, lambda, and class bodies are not attributed to the caller;
    - an alias that shadows a same-file top-level function is skipped;
    - the example is discarded if the alias or the target's real name survives
      anywhere in the rendered caller text;
    - every candidate shares the target's AST call shape and excludes the caller;
    - candidates are drawn from the whole repository, so the caller's own file
      is not privileged;
    - examples that cannot fill the candidate count are skipped.

    ``source_roots`` names directories, relative to the repository root, under
    which absolute imports may also resolve (a declared or conventional source
    root such as ``src``). Resolution is conservative: see ``_module_file``.
    """
    if candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")
    roots = tuple(Path(root).as_posix() for root in source_roots)

    root_path = Path(root).resolve()
    all_symbols, by_file = collect_python_symbols(root_path, strict=strict)
    known_files = frozenset(by_file)
    examples: list[DecisionExample] = []

    for source_name, local_symbols in sorted(by_file.items()):
        path = root_path / source_name
        try:
            source_text = path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=source_name)
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
        imports = {
            alias: symbol for alias, symbol in imports.items()
            if alias not in local_names
        }
        if not imports:
            continue

        by_name = {symbol.name: symbol for symbol in local_symbols}
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            caller = by_name.get(node.name)
            if caller is None:
                continue
            visitor = _DirectCallVisitor(node, set(imports))
            visitor.visit(node)
            aliases = tuple(dict.fromkeys(visitor.targets))
            if len(aliases) != 1:
                continue
            alias = aliases[0]
            target = imports[alias]

            masked_body = _masked_function_body(
                source_text, caller_name=node.name, target_name=alias
            )
            if masked_body is None:
                continue
            if alias != target.name and re.search(
                rf"\b{re.escape(target.name)}\b", masked_body
            ):
                continue

            pool = [
                symbol for symbol in all_symbols
                if symbol != caller and symbol.call_shape == target.call_shape
            ]
            if target not in pool or len(pool) < candidate_count:
                continue

            rng = _stable_rng(
                seed, "hard-cross-file", source_name, node.name, target.candidate
            )
            negatives = [symbol for symbol in pool if symbol != target]
            rng.shuffle(negatives)
            chosen = [target, *negatives[: candidate_count - 1]]
            rng.shuffle(chosen)

            examples.append(DecisionExample(
                context=masked_body,
                question=(
                    "Which candidate definition should replace "
                    "__CALL_TARGET__ in this caller?"
                ),
                candidates=tuple(
                    f"{symbol.signature}\n{symbol.body[:candidate_body_chars]}"
                    for symbol in chosen
                ),
                answer_index=chosen.index(target),
                task=TASK,
                source=source_name,
            ))

    return examples
