"""Controlled text ablations for decision-model experiments."""
from __future__ import annotations

import ast
import re
from dataclasses import replace

from .synthetic import DecisionExample


class _OwnNameMasker(ast.NodeTransformer):
    """Rename one function definition and references to its own identifier."""

    def __init__(self, original: str, replacement: str) -> None:
        self.original = original
        self.replacement = replacement

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node = self.generic_visit(node)
        if node.name == self.original:
            node.name = self.replacement
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        node = self.generic_visit(node)
        if node.name == self.original:
            node.name = self.replacement
        return node

    def visit_Name(self, node: ast.Name):
        if node.id == self.original:
            return ast.copy_location(
                ast.Name(id=self.replacement, ctx=node.ctx),
                node,
            )
        return node


def _rename_outer_function(text: str, replacement: str) -> str:
    tree = ast.parse(text)
    outer = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        None,
    )
    if outer is None:
        raise ValueError("expected a function definition")
    original = outer.name
    tree = _OwnNameMasker(original, replacement).visit(tree)
    ast.fix_missing_locations(tree)
    rendered = ast.unparse(tree)
    return re.sub(rf"\b{re.escape(original)}\b", replacement, rendered)


def ablate_hard_call_identifiers(
    example: DecisionExample,
    *,
    caller: bool = True,
    candidates: bool = True,
) -> DecisionExample:
    """Mask caller/candidate own identifiers while preserving the correct option.

    Intended for hard masked-call examples where candidate text contains a signature
    line followed by a function body. Every candidate receives the same replacement
    identifier so the ablation cannot encode candidate position.
    """
    if not caller and not candidates:
        return example
    if example.task != "python.hard_masked_direct_call":
        raise ValueError("identifier ablation expects a hard masked-call example")

    context = (
        _rename_outer_function(example.context, "__CALLER__")
        if caller
        else example.context
    )

    transformed = example.candidates
    if candidates:
        out = []
        for candidate in example.candidates:
            if "\n" not in candidate:
                raise ValueError("expected candidate signature followed by function body")
            _, body = candidate.split("\n", 1)
            out.append(_rename_outer_function(body, "__CANDIDATE__"))
        transformed = tuple(out)

    return replace(
        example,
        context=context,
        candidates=transformed,
    )
