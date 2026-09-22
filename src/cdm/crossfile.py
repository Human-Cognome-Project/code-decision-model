"""Machine-verified cross-file call supervision (E029).

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
    root: Path,
    known_files: frozenset[str],
    importing_file: Path,
    module: str | None,
    level: int,
) -> str | None:
    """Resolve an import statement to a repository-relative Python file.

    Absolute imports are tried at the repository root, then at each ancestor
    directory of the importing file (nearest first), then at each first-level
    directory of the repository in sorted order, so ``src/`` layouts resolve
    both from inside the package and from sibling test trees. Relative imports
    follow the usual package rules. The result must be a file the extractor
    already parsed; anything else (third-party, stdlib, missing) returns None.
    """
    parts = tuple(module.split(".")) if module else ()

    if level == 0:
        bases = [Path("."), *importing_file.parents, *_source_roots(known_files)]
    else:
        base = importing_file.parent
        for _ in range(level - 1):
            base = base.parent
        bases = [base]

    for base in bases:
        target = base.joinpath(*parts) if parts else base
        for candidate in (target.with_suffix(".py"), target / "__init__.py"):
            rel = candidate.as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            if rel in known_files:
                return rel
    return None


def _source_roots(known_files: frozenset[str]) -> tuple[Path, ...]:
    """First-level repository directories that contain parsed Python files."""
    roots = {Path(rel).parts[0] for rel in known_files if len(Path(rel).parts) > 1}
    return tuple(Path(name) for name in sorted(roots))


def _cross_file_imports(
    tree: ast.Module,
    *,
    root: Path,
    known_files: frozenset[str],
    importing_file: Path,
    by_file: dict[str, tuple[PythonSymbol, ...]],
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
            root, known_files, importing_file, statement.module, statement.level
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
    """
    if candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")

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
            root=root_path,
            known_files=known_files,
            importing_file=Path(source_name),
            by_file=by_file,
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
