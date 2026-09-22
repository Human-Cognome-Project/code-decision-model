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
    task: str = "unspecified"
    source: str | None = None


def _top_level_functions(source: str):
    tree = ast.parse(source)
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _signatures(funcs) -> tuple[str, ...]:
    return tuple(
        f"{node.name}({', '.join(arg.arg for arg in node.args.args)})"
        for node in funcs
    )


def python_definition_examples(source: str) -> list[DecisionExample]:
    """Create symbol-definition decisions whose labels come directly from Python's AST."""
    funcs = _top_level_functions(source)
    if len(funcs) < 2:
        return []

    candidates = _signatures(funcs)
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


def python_direct_call_examples(source: str) -> list[DecisionExample]:
    """Create direct-call decisions from exact AST facts.

    A function becomes an example only when it calls exactly one distinct top-level
    function from the same module. Calls to builtins and external names are ignored.
    The target is therefore deterministic and requires no model-generated labels.
    """
    funcs = _top_level_functions(source)
    if len(funcs) < 2:
        return []

    index = {node.name: i for i, node in enumerate(funcs)}
    candidates = _signatures(funcs)
    examples: list[DecisionExample] = []

    for node in funcs:
        local_calls: list[str] = []
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Name)
                and child.func.id in index
                and child.func.id != node.name
            ):
                local_calls.append(child.func.id)

        # dict preserves first-seen order while removing duplicates.
        unique_calls = tuple(dict.fromkeys(local_calls))
        if len(unique_calls) != 1:
            continue

        target = unique_calls[0]
        context = ast.get_source_segment(source, node) or node.name
        examples.append(
            DecisionExample(
                context=context,
                question=f"Which candidate function is directly called by {node.name}?",
                candidates=candidates,
                answer_index=index[target],
            )
        )

    return examples
