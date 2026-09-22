"""Context focusing transforms for code-decision experiments."""
from __future__ import annotations

import ast
import re
from dataclasses import replace

from .synthetic import DecisionExample


_DEF = re.compile(r"^\s*(?:async\s+def|def)\s+")


def focus_hard_call_context(
    example: DecisionExample,
    *,
    radius_lines: int = 8,
    marker: str = "__CALL_TARGET__",
    compact_header: bool = False,
) -> DecisionExample:
    """Keep a function header and a local line window around the masked call site.

    This transform is intended for hard masked-call examples. It never changes the
    candidate set or answer. Short contexts are returned unchanged.
    """
    if example.task != "python.hard_masked_direct_call":
        raise ValueError("call-site focusing expects a hard masked-call example")
    if radius_lines < 0:
        raise ValueError("radius_lines must be non-negative")

    lines = example.context.splitlines()
    marker_lines = [i for i, line in enumerate(lines) if marker in line]
    if not marker_lines:
        raise ValueError(f"marker {marker!r} not found in context")

    header = next((i for i, line in enumerate(lines) if _DEF.match(line)), None)
    if header is None:
        raise ValueError("function definition header not found")

    # Multiple appearances are rare but possible if the same masked callee is called
    # more than once. Center the retained region across the first/last occurrence.
    first_marker = marker_lines[0]
    last_marker = marker_lines[-1]
    start = max(header + 1, first_marker - radius_lines)
    end = min(len(lines), last_marker + radius_lines + 1)

    # If the requested window already covers the complete function, keep exact text
    # unless the caller explicitly asked to compact the header.
    if (
        not compact_header
        and start == header + 1
        and end == len(lines)
        and header == 0
    ):
        return example

    if compact_header:
        tree = ast.parse(example.context)
        outer = next(
            (
                node
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ),
            None,
        )
        if outer is None:
            raise ValueError("function definition header not found")
        prefix = [
            ("async def " if isinstance(outer, ast.AsyncFunctionDef) else "def ")
            + f"{outer.name}(...):"
        ]
    else:
        prefix = lines[: header + 1]
    indent_match = re.match(r"^(\s*)", lines[first_marker])
    body_indent = indent_match.group(1) if indent_match else "    "
    if not body_indent:
        body_indent = "    "

    focused = list(prefix)
    if start > header + 1:
        focused.append(body_indent + "# ... omitted before call site ...")
    focused.extend(lines[start:end])
    if end < len(lines):
        focused.append(body_indent + "# ... omitted after call site ...")

    return replace(example, context="\n".join(focused))
