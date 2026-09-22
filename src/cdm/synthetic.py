"""Machine-verifiable synthetic tasks for the first experiment."""
from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionExample:
    context: str
    question: str
    candidates: tuple[str, ...]
    answer_index: int


def python_definition_examples(source: str) -> list[DecisionExample]:
    """Create symbol-definition decisions whose labels come directly from Python's AST.

    Each top-level function becomes a query. Distractors are the other functions in the
    same module. This is intentionally simple: it proves the data path before richer LSP,
    compiler, call-graph, and patch-derived supervision is added.
    """
    tree = ast.parse(source)
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(funcs) < 2:
        return []

    candidates = tuple(
        f"{node.name}({', '.join(a.arg for a in node.args.args)})"
        for node in funcs
    )
    examples: list[DecisionExample] = []
    for i, node in enumerate(funcs):
        context = ast.get_source_segment(source, node) or node.name
        examples.append(
            DecisionExample(
                context=context,
                question=f"Which candidate is the definition of symbol {node.name}?",
                candidates=candidates,
                answer_index=i,
            )
        )
    return examples
