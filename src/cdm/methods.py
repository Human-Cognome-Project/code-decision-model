"""Machine-verified same-class method-call supervision."""
from __future__ import annotations

import ast
import copy
import hashlib
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .repository import iter_python_files
from .synthetic import DecisionExample


@dataclass(frozen=True)
class MethodSymbol:
    source: str
    class_name: str
    name: str
    signature: str
    body: str
    binding_kind: str
    call_shape: tuple[int, int, int, int, bool, bool, bool]

    @property
    def identity(self) -> str:
        return f"{self.source}::{self.class_name}.{self.signature}"


def _decorator_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return None


def _binding_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    names = {_decorator_name(d) for d in node.decorator_list}
    if names & {"property", "setter", "getter", "deleter"}:
        return None
    if "staticmethod" in names:
        return "static"
    if "classmethod" in names:
        return "class"
    return "instance"


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
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


def _invocation_shape(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    binding_kind: str,
) -> tuple[int, int, int, int, bool, bool, bool]:
    positional = len(node.args.posonlyargs) + len(node.args.args)
    required_positional = positional - len(node.args.defaults)
    if binding_kind in {"instance", "class"} and positional:
        positional -= 1
        required_positional = max(0, required_positional - 1)
    keyword_only = len(node.args.kwonlyargs)
    required_keyword_only = sum(default is None for default in node.args.kw_defaults)
    return (
        positional,
        required_positional,
        keyword_only,
        required_keyword_only,
        node.args.vararg is not None,
        node.args.kwarg is not None,
        isinstance(node, ast.AsyncFunctionDef),
    )


def _first_receiver_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    positional = [*node.args.posonlyargs, *node.args.args]
    return positional[0].arg if positional else None


def _stable_rng(*parts: object) -> random.Random:
    payload = "\x1f".join(str(p) for p in parts).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
    return random.Random(seed)


class _MethodCallVisitor(ast.NodeVisitor):
    def __init__(self, root, receivers: set[str], local_names: set[str]) -> None:
        self.root = root
        self.receivers = receivers
        self.local_names = local_names
        self.targets: list[str] = []

    def _visit_root(self, node) -> None:
        if node is self.root:
            for statement in node.body:
                self.visit(statement)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_root(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_root(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in self.receivers
            and func.attr in self.local_names
            and func.attr != self.root.name
        ):
            self.targets.append(func.attr)
        self.generic_visit(node)


class _TargetAttributeMasker(ast.NodeTransformer):
    def __init__(self, target: str, receivers: set[str]) -> None:
        self.target = target
        self.receivers = receivers

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if (
            node.attr == self.target
            and isinstance(node.value, ast.Name)
            and node.value.id in self.receivers
        ):
            node.attr = "__CALL_TARGET__"
        return node


def _collect_methods(
    source: str,
    source_name: str,
    class_node: ast.ClassDef,
) -> tuple[tuple[MethodSymbol, ...], dict[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    nodes = [
        n for n in class_node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    counts = Counter(n.name for n in nodes)
    symbols: list[MethodSymbol] = []
    kept_nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in nodes:
        if counts[node.name] != 1:
            continue
        binding = _binding_kind(node)
        if binding is None:
            continue
        body = ast.get_source_segment(source, node) or ast.unparse(node)
        symbols.append(MethodSymbol(
            source=source_name,
            class_name=class_node.name,
            name=node.name,
            signature=_signature(node),
            body=body,
            binding_kind=binding,
            call_shape=_invocation_shape(node, binding),
        ))
        kept_nodes[node.name] = node
    return tuple(symbols), kept_nodes


def _receivers(
    caller: ast.FunctionDef | ast.AsyncFunctionDef,
    class_name: str,
    binding_kind: str,
) -> set[str]:
    result = {class_name}
    if binding_kind in {"instance", "class"}:
        receiver = _first_receiver_name(caller)
        if receiver:
            result.add(receiver)
    return result


def _masked_method(
    caller: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    target_name: str,
    receivers: set[str],
) -> str | None:
    masked = copy.deepcopy(caller)
    masked = _TargetAttributeMasker(target_name, receivers).visit(masked)
    ast.fix_missing_locations(masked)
    rendered = ast.unparse(masked)
    if "__CALL_TARGET__" not in rendered:
        return None
    if re.search(rf"\b{re.escape(target_name)}\b", rendered):
        return None
    return rendered


def repository_hard_masked_method_call_examples(
    root: str | Path,
    *,
    candidate_count: int = 4,
    candidate_body_chars: int = 768,
    seed: int = 0,
    strict: bool = False,
) -> list[DecisionExample]:
    """Create same-class method-call decisions with exact AST-derived labels."""
    if candidate_count < 2:
        raise ValueError("candidate_count must be at least 2")

    root_path = Path(root).resolve()
    examples: list[DecisionExample] = []
    for rel in iter_python_files(root_path):
        path = root_path / rel
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=rel.as_posix())
        except (OSError, UnicodeError, SyntaxError):
            if strict:
                raise
            continue

        for class_node in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            symbols, nodes = _collect_methods(source, rel.as_posix(), class_node)
            if len(symbols) < candidate_count + 1:
                continue
            by_name = {s.name: s for s in symbols}
            local_names = set(by_name)

            for caller_name, caller_node in sorted(nodes.items()):
                caller_symbol = by_name[caller_name]
                receivers = _receivers(caller_node, class_node.name, caller_symbol.binding_kind)
                visitor = _MethodCallVisitor(caller_node, receivers, local_names)
                visitor.visit(caller_node)
                targets = tuple(dict.fromkeys(visitor.targets))
                if len(targets) != 1:
                    continue
                target_name = targets[0]
                target = by_name[target_name]
                context = _masked_method(
                    caller_node, target_name=target_name, receivers=receivers
                )
                if context is None:
                    continue

                pool = [
                    symbol for symbol in symbols
                    if symbol != caller_symbol
                    and symbol.binding_kind == target.binding_kind
                    and symbol.call_shape == target.call_shape
                ]
                if target not in pool or len(pool) < candidate_count:
                    continue

                rng = _stable_rng(
                    seed, "hard-method", rel.as_posix(), class_node.name,
                    caller_name, target.identity
                )
                negatives = [s for s in pool if s != target]
                rng.shuffle(negatives)
                chosen = [target, *negatives[: candidate_count - 1]]
                rng.shuffle(chosen)
                candidates = tuple(
                    f"{s.signature}\n{s.body[:candidate_body_chars]}" for s in chosen
                )
                examples.append(DecisionExample(
                    context=context,
                    question=(
                        "Which candidate method should replace __CALL_TARGET__ "
                        "in this caller?"
                    ),
                    candidates=candidates,
                    answer_index=chosen.index(target),
                    task="python.hard_masked_same_class_call",
                    source=rel.as_posix(),
                ))

    return examples
