"""Deterministic corrective-turn harness for masked call-repair experiments."""
from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass

from .synthetic import DecisionExample


_SUPPORTED_TASKS = frozenset({
    "python.hard_masked_direct_call",
    "python.hard_masked_same_class_call",
})
_SIGNATURE = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)[ 	]*[(]")


@dataclass(frozen=True)
class RepairVerification:
    """Result of deterministic verification for one generated repair."""

    valid: bool
    reason: str


@dataclass(frozen=True)
class RepairAttempt:
    """One generator attempt and its deterministic verification."""

    prompt: str
    output: str
    verification: RepairVerification


@dataclass(frozen=True)
class RepairOutcome:
    """Complete correction loop for one repair task."""

    success: bool
    attempts: tuple[RepairAttempt, ...]

    @property
    def attempts_used(self) -> int:
        return len(self.attempts)

    @property
    def correction_turns(self) -> int:
        """Regeneration turns after the initial generation attempt."""
        return max(0, self.attempts_used - 1)

    @property
    def first_pass_success(self) -> bool:
        return bool(self.attempts) and self.attempts[0].verification.valid


@dataclass(frozen=True)
class PairedRepairOutcome:
    """Baseline and decision-assisted outcomes for the same repair task."""

    baseline: RepairOutcome
    assisted: RepairOutcome

    @property
    def success_delta(self) -> int:
        return int(self.assisted.success) - int(self.baseline.success)

    @property
    def correction_turn_delta(self) -> int | None:
        """Baseline minus assisted corrections when both conditions resolve."""
        if not (self.baseline.success and self.assisted.success):
            return None
        return self.baseline.correction_turns - self.assisted.correction_turns


def candidate_symbol(candidate: str) -> str:
    """Extract the callable symbol name from a rendered candidate definition."""
    first = candidate.splitlines()[0].strip()
    match = _SIGNATURE.match(first)
    if match is None:
        raise ValueError(
            f"candidate does not begin with a function signature: {first!r}"
        )
    return match.group(1)


def extract_python(text: str) -> str:
    """Extract one fenced code block or return stripped raw output."""
    stripped = text.strip()
    fence = chr(96) * 3
    if stripped.startswith(fence):
        first_newline = stripped.find(chr(10))
        closing = stripped.rfind(fence)
        if first_newline >= 0 and closing > first_newline:
            return stripped[first_newline + 1 : closing].strip()
    return stripped


class _ResolveMarker(ast.NodeTransformer):
    def __init__(self, target: str) -> None:
        self.target = target

    def visit_Name(self, node: ast.Name):
        if node.id == "__CALL_TARGET__":
            return ast.copy_location(
                ast.Name(id=self.target, ctx=node.ctx),
                node,
            )
        return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if node.attr == "__CALL_TARGET__":
            node.attr = self.target
        return node


def _parsed_function(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(
        tree.body[0],
        (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        raise ValueError("repair source must contain only one top-level function")
    return tree.body[0]


def expected_repair_source(example: DecisionExample) -> str:
    """Return the machine-derived target repair as normalized Python source."""
    if example.task not in _SUPPORTED_TASKS:
        raise ValueError("repair harness expects a hard masked-call example")

    target = candidate_symbol(example.candidates[example.answer_index])
    tree = ast.parse(example.context)
    resolved = _ResolveMarker(target).visit(tree)
    ast.fix_missing_locations(resolved)

    if any(
        (
            isinstance(node, ast.Name) and node.id == "__CALL_TARGET__"
        )
        or (
            isinstance(node, ast.Attribute) and node.attr == "__CALL_TARGET__"
        )
        for node in ast.walk(resolved)
    ):
        raise ValueError("masked call marker was not fully resolved")

    return ast.unparse(resolved)


def verify_repair(
    example: DecisionExample,
    generated: str,
) -> RepairVerification:
    """Require generated caller to equal the exact target repair modulo formatting."""
    if example.task not in _SUPPORTED_TASKS:
        return RepairVerification(False, "unsupported_task")

    code = extract_python(generated)
    try:
        expected = _parsed_function(expected_repair_source(example))
        actual = _parsed_function(code)
    except (SyntaxError, ValueError):
        return RepairVerification(False, "invalid_python")

    if actual.name != expected.name or type(actual) is not type(expected):
        return RepairVerification(False, "wrong_function")

    if any(
        (
            isinstance(node, ast.Name) and node.id == "__CALL_TARGET__"
        )
        or (
            isinstance(node, ast.Attribute) and node.attr == "__CALL_TARGET__"
        )
        for node in ast.walk(actual)
    ):
        return RepairVerification(False, "placeholder_remaining")

    expected_dump = ast.dump(expected, include_attributes=False)
    actual_dump = ast.dump(actual, include_attributes=False)
    if actual_dump != expected_dump:
        target = candidate_symbol(example.candidates[example.answer_index])
        candidate_names = {
            candidate_symbol(candidate)
            for candidate in example.candidates
        }
        called_names: set[str] = set()

        for node in ast.walk(actual):
            if not isinstance(node, ast.Call):
                continue
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in candidate_names
            ):
                called_names.add(node.func.id)
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in candidate_names
            ):
                called_names.add(node.func.attr)

        if called_names and target not in called_names:
            return RepairVerification(False, "wrong_target")
        return RepairVerification(False, "unrelated_change")

    return RepairVerification(True, "ok")


def feedback_for(verification: RepairVerification) -> str:
    """Return verifier feedback without revealing the correct target."""
    messages = {
        "invalid_python": (
            "The repair is not a single valid Python function. "
            "Return a complete function."
        ),
        "wrong_function": (
            "The caller identity changed. Preserve the original caller and "
            "revise only the repair."
        ),
        "placeholder_remaining": (
            "The masked call target is still present. Replace it with one "
            "candidate."
        ),
        "wrong_target": (
            "The selected call target violates the repository constraint. "
            "Reconsider the candidates."
        ),
        "unrelated_change": (
            "The repair changed code outside the masked call target. Make "
            "only the required call-target edit."
        ),
        "unsupported_task": "This task is not supported by the repair verifier.",
    }
    return messages.get(
        verification.reason,
        "The deterministic verifier rejected the repair. Revise the function.",
    )


def build_repair_prompt(
    example: DecisionExample,
    *,
    recommendation_index: int | None = None,
    previous_output: str | None = None,
    feedback: str | None = None,
) -> str:
    """Build repair prompt with an optional fallible decision recommendation."""
    if example.task not in _SUPPORTED_TASKS:
        raise ValueError("repair prompt expects a hard masked-call example")
    if recommendation_index is not None and not (
        0 <= recommendation_index < len(example.candidates)
    ):
        raise ValueError("recommendation_index is out of range")

    nl = chr(10)
    candidates = (nl + nl).join(
        f"Candidate {index + 1}:{nl}{candidate}"
        for index, candidate in enumerate(example.candidates)
    )
    sections = [
        "Repair the Python caller below.",
        (
            "Replace __CALL_TARGET__ with the correct candidate while "
            "preserving every other operation. Return only the complete "
            "repaired Python function."
        ),
        "Caller:" + nl + example.context,
        "Candidates:" + nl + candidates,
    ]

    if recommendation_index is not None:
        sections.append(
            "Repository decision evidence (fallible): "
            f"candidate {recommendation_index + 1} is recommended. "
            "Use this as evidence, but still verify it against the code."
        )

    if previous_output is not None and feedback is not None:
        sections.extend([
            "Previous attempt:" + nl + previous_output,
            "Deterministic verifier feedback:" + nl + feedback,
            "Return a revised complete Python function only.",
        ])

    return (nl + nl).join(sections)


def run_repair_loop(
    example: DecisionExample,
    generate: Callable[[str], str],
    *,
    recommendation_index: int | None = None,
    max_attempts: int = 3,
) -> RepairOutcome:
    """Run bounded generate, verify, corrective-feedback iterations."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    attempts: list[RepairAttempt] = []
    previous_output: str | None = None
    feedback: str | None = None

    for _ in range(max_attempts):
        prompt = build_repair_prompt(
            example,
            recommendation_index=recommendation_index,
            previous_output=previous_output,
            feedback=feedback,
        )
        output = generate(prompt)
        verification = verify_repair(example, output)
        attempts.append(
            RepairAttempt(
                prompt=prompt,
                output=output,
                verification=verification,
            )
        )
        if verification.valid:
            return RepairOutcome(True, tuple(attempts))

        previous_output = output
        feedback = feedback_for(verification)

    return RepairOutcome(False, tuple(attempts))


def run_paired_repair(
    example: DecisionExample,
    generate_factory: Callable[[], Callable[[str], str]],
    *,
    recommendation_index: int,
    max_attempts: int = 3,
) -> PairedRepairOutcome:
    """Run baseline and decision-assisted repair with fresh generator instances."""
    baseline = run_repair_loop(
        example,
        generate_factory(),
        recommendation_index=None,
        max_attempts=max_attempts,
    )
    assisted = run_repair_loop(
        example,
        generate_factory(),
        recommendation_index=recommendation_index,
        max_attempts=max_attempts,
    )
    return PairedRepairOutcome(
        baseline=baseline,
        assisted=assisted,
    )
