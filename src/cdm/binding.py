"""Deterministic call-site bindability predicate.

E019 introduced the hard-constraint interface with placeholder substring checks.
This module supplies the first constraint derived from real machine-checkable
facts: a candidate definition is legal only if Python's argument-binding rules
could bind every masked call site in the caller.

Everything comes from the AST. The predicate never consults a model, and missing
information never vetoes: an unparseable caller, an absent call site, or an
unreadable candidate signature leaves the candidate allowed. The implementation
is deliberately biased toward avoiding false vetoes; current labelled corpora and
tests act as empirical soundness regression checks rather than a universal proof.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Sequence

from .constraints import ConstraintResult

MARKER = "__CALL_TARGET__"


@dataclass(frozen=True)
class CallShape:
    """How one masked call site invokes its target."""

    positional: int
    """Known positional arguments. A lower bound when ``starred`` is set."""

    keywords: frozenset[str]
    """Explicit keyword names. A lower bound when ``double_starred`` is set."""

    starred: bool
    double_starred: bool
    receiver: bool
    """True for attribute form ``recv.__CALL_TARGET__(...)``."""


@dataclass(frozen=True)
class Parameters:
    """Binding-relevant view of a candidate definition's parameters."""

    positional_only: tuple[str, ...]
    positional_or_keyword: tuple[str, ...]
    keyword_only: tuple[str, ...]
    required: frozenset[str]
    has_vararg: bool
    has_kwarg: bool
    defaults_known: bool

    @property
    def positional(self) -> tuple[str, ...]:
        return self.positional_only + self.positional_or_keyword


def call_shapes(context: str, *, marker: str = MARKER) -> tuple[CallShape, ...]:
    """Extract every call of the masked marker from the caller source."""
    try:
        tree = ast.parse(context)
    except (SyntaxError, ValueError):
        return ()

    shapes: list[CallShape] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == marker:
            receiver = False
        elif isinstance(func, ast.Attribute) and func.attr == marker:
            receiver = True
        else:
            continue
        shapes.append(
            CallShape(
                positional=sum(
                    not isinstance(arg, ast.Starred) for arg in node.args
                ),
                keywords=frozenset(
                    kw.arg for kw in node.keywords if kw.arg is not None
                ),
                starred=any(isinstance(arg, ast.Starred) for arg in node.args),
                double_starred=any(kw.arg is None for kw in node.keywords),
                receiver=receiver,
            )
        )
    return tuple(shapes)


def parameters_from_arguments(
    args: ast.arguments,
    *,
    defaults_known: bool = True,
) -> Parameters:
    """Summarise an ``ast.arguments`` node for binding checks."""
    positional_only = tuple(arg.arg for arg in args.posonlyargs)
    positional_or_keyword = tuple(arg.arg for arg in args.args)
    keyword_only = tuple(arg.arg for arg in args.kwonlyargs)

    required: set[str] = set()
    if defaults_known:
        positional = positional_only + positional_or_keyword
        optional_from = len(positional) - len(args.defaults)
        required.update(positional[:optional_from])
        required.update(
            name
            for name, default in zip(keyword_only, args.kw_defaults)
            if default is None
        )

    return Parameters(
        positional_only=positional_only,
        positional_or_keyword=positional_or_keyword,
        keyword_only=keyword_only,
        required=frozenset(required),
        has_vararg=args.vararg is not None,
        has_kwarg=args.kwarg is not None,
        defaults_known=defaults_known,
    )


def _parse_definition(header: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    try:
        tree = ast.parse(header)
    except (SyntaxError, ValueError):
        return None
    if len(tree.body) == 1 and isinstance(
        tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        return tree.body[0]
    return None


def _definition_from_body(body: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Recover the full ``def`` header (with defaults) from a rendered body.

    The body excerpt may be truncated, so the header is located by the first
    colon at parenthesis depth zero that yields a parseable definition.
    """
    stripped = body.lstrip()
    if not (stripped.startswith("def ") or stripped.startswith("async def ")):
        return None

    depth = 0
    for index, char in enumerate(stripped):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == ":" and depth == 0:
            node = _parse_definition(stripped[: index + 1] + " pass")
            if node is not None:
                return node
    return None


def candidate_parameters(candidate: str) -> Parameters | None:
    """Read parameters from a rendered candidate.

    Candidates begin with a signature line such as ``name(a, b, /, *, c)``,
    optionally prefixed by ``source::``. When a definition body follows, its
    header supplies default information; otherwise every parameter is treated
    as optional so unknown defaults can never veto.
    """
    lines = candidate.strip().splitlines()
    if not lines:
        return None

    signature = lines[0].strip()
    if "::" in signature:
        signature = signature.rsplit("::", 1)[1]

    body = "\n".join(lines[1:])
    node = _definition_from_body(body) if body.strip() else None
    if node is not None:
        return parameters_from_arguments(node.args, defaults_known=True)

    node = _parse_definition(f"def {signature}: pass")
    if node is None:
        return None
    return parameters_from_arguments(node.args, defaults_known=False)


def binds(
    parameters: Parameters,
    shape: CallShape,
    *,
    drop_receiver: bool = False,
) -> bool:
    """Decide whether Python could bind ``shape`` to ``parameters``.

    Unknown quantities (starred call arguments, unknown defaults) are always
    resolved in the candidate's favour.
    """
    positional_only = parameters.positional_only
    positional_or_keyword = parameters.positional_or_keyword
    if drop_receiver:
        if positional_only:
            positional_only = positional_only[1:]
        elif positional_or_keyword:
            positional_or_keyword = positional_or_keyword[1:]
    positional = positional_only + positional_or_keyword

    if shape.positional > len(positional) and not parameters.has_vararg:
        return False

    # Positional slots are only known exactly when nothing is starred.
    filled = set() if shape.starred else set(positional[: shape.positional])

    for keyword in shape.keywords:
        if keyword in positional_only:
            return False
        if keyword in filled:
            return False
        if (
            keyword not in positional_or_keyword
            and keyword not in parameters.keyword_only
            and not parameters.has_kwarg
        ):
            return False

    for name in parameters.required:
        if name in filled or name in shape.keywords:
            continue
        if name in positional:
            if shape.starred:
                continue
            if name in positional_or_keyword and shape.double_starred:
                continue
            return False
        if name in parameters.keyword_only:
            if shape.double_starred:
                continue
            return False
        # A dropped receiver parameter is bound by the receiver itself.

    return True


def candidate_bindable(
    parameters: Parameters,
    shapes: Sequence[CallShape],
) -> bool:
    """A candidate is legal only if every masked call site can bind it.

    Attribute-form call sites may target instance/class methods (receiver bound
    implicitly) or static methods (no implicit receiver). Either reading counts.
    """
    for shape in shapes:
        if shape.receiver:
            if binds(parameters, shape, drop_receiver=True):
                continue
            if binds(parameters, shape, drop_receiver=False):
                continue
            return False
        if not binds(parameters, shape):
            return False
    return True


@dataclass(frozen=True)
class CallSiteBindable:
    """Hard constraint: the masked call site must be able to bind the candidate."""

    marker: str = MARKER

    def check(
        self,
        code_context: str,
        question: str,
        candidates: Sequence[str],
    ) -> ConstraintResult:
        shapes = call_shapes(code_context, marker=self.marker)
        if not shapes:
            return ConstraintResult(allowed=tuple(True for _ in candidates))

        allowed: list[bool] = []
        reasons: list[str] = []
        for candidate in candidates:
            parameters = candidate_parameters(candidate)
            if parameters is None:
                allowed.append(True)
                reasons.append("")
                continue
            ok = candidate_bindable(parameters, shapes)
            allowed.append(ok)
            reasons.append("" if ok else "call site cannot bind candidate signature")
        return ConstraintResult(allowed=tuple(allowed), reasons=tuple(reasons))
