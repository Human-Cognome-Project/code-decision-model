"""E033 call-expression intent: one step richer than a candidate index.

E022 asked a compact generator for a whole repaired function and it never
crossed the validity floor. E023 asked for a candidate index and the decision
layer's effect became measurable. E033 sits between them: the generator emits
exactly one Python call expression, callee and arguments, and deterministic code
splices it over the masked call in the caller's AST.

The output is a real code fragment, so three deterministic checks apply before
any comparison with the machine-labelled repair:

1. it must parse as a single call expression;
2. its callee must name exactly one candidate (never resolved via the label);
3. it must be bindable against that candidate's real signature (E024).

Only then is the spliced caller compared, AST to AST, with the E021 expected
repair. Feedback names the failure category and never the correct target.
"""
from __future__ import annotations

import ast
import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .binding import candidate_bindable, candidate_parameters, shape_of_call
from .repair import candidate_symbol, expected_repair_source, extract_python
from .synthetic import DecisionExample

MARKER = "__CALL_TARGET__"
_SUPPORTED_TASKS = frozenset({
    "python.hard_masked_direct_call",
    "python.hard_masked_same_class_call",
    "python.hard_masked_cross_file_call",
})


@dataclass(frozen=True)
class CallIntentVerification:
    valid: bool
    reason: str
    target_index: int | None = None


@dataclass(frozen=True)
class CallIntentAttempt:
    prompt: str
    output: str
    verification: CallIntentVerification


@dataclass(frozen=True)
class CallIntentOutcome:
    success: bool
    attempts: tuple[CallIntentAttempt, ...]

    @property
    def attempts_used(self) -> int:
        return len(self.attempts)

    @property
    def correction_turns(self) -> int:
        return max(0, self.attempts_used - 1)

    @property
    def first_pass_success(self) -> bool:
        return bool(self.attempts) and self.attempts[0].verification.valid


@dataclass(frozen=True)
class PairedCallIntentOutcome:
    baseline: CallIntentOutcome
    assisted: CallIntentOutcome

    @property
    def success_delta(self) -> int:
        return int(self.assisted.success) - int(self.baseline.success)

    @property
    def correction_turn_delta(self) -> int | None:
        if not (self.baseline.success and self.assisted.success):
            return None
        return self.baseline.correction_turns - self.assisted.correction_turns


def _is_marker_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == MARKER)
        or (isinstance(node.func, ast.Attribute) and node.func.attr == MARKER)
    )


def masked_call_count(example: DecisionExample) -> int:
    """Number of masked call sites; E033 supports exactly one."""
    try:
        tree = ast.parse(example.context)
    except (SyntaxError, ValueError):
        return 0
    return sum(_is_marker_call(node) for node in ast.walk(tree))


def eligible(example: DecisionExample) -> bool:
    return example.task in _SUPPORTED_TASKS and masked_call_count(example) == 1


def parse_call_intent(text: str) -> ast.Call | None:
    """Parse generator output as exactly one call expression, else None."""
    code = extract_python(text).strip().strip("`").strip()
    if code.endswith(";"):
        code = code[:-1].rstrip()
    try:
        tree = ast.parse(code, mode="eval")
    except (SyntaxError, ValueError):
        return None
    node = tree.body
    if not isinstance(node, ast.Call):
        return None
    if isinstance(node.func, ast.Name):
        return node
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node
    return None


def intent_callee(call: ast.Call) -> str:
    return call.func.id if isinstance(call.func, ast.Name) else call.func.attr


def candidate_indices_for(example: DecisionExample, callee: str) -> tuple[int, ...]:
    """Every candidate whose symbol equals the callee, in candidate order.

    Resolution never consults the label. Repository-wide pools (E030) do not
    guarantee unique symbol names, so a callee can match zero, one, or several
    candidates; the verifier treats anything but exactly one as a failure.
    """
    return tuple(
        index for index, candidate in enumerate(example.candidates)
        if candidate_symbol(candidate) == callee
    )


class _SpliceIntent(ast.NodeTransformer):
    def __init__(self, replacement: ast.Call) -> None:
        self.replacement = replacement

    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        if _is_marker_call(node):
            return ast.copy_location(copy.deepcopy(self.replacement), node)
        return node


def apply_call_intent(example: DecisionExample, call: ast.Call) -> str:
    """Replace the masked call with the intent and return normalized source."""
    tree = ast.parse(example.context)
    spliced = _SpliceIntent(call).visit(tree)
    ast.fix_missing_locations(spliced)
    return ast.unparse(spliced)


def verify_call_intent(
    example: DecisionExample,
    generated: str,
) -> CallIntentVerification:
    """Deterministic verification of one generated call expression."""
    if example.task not in _SUPPORTED_TASKS:
        return CallIntentVerification(False, "unsupported_task")
    if masked_call_count(example) != 1:
        return CallIntentVerification(False, "unsupported_task")

    call = parse_call_intent(generated)
    if call is None:
        return CallIntentVerification(False, "invalid_call_expression")

    matches = candidate_indices_for(example, intent_callee(call))
    if not matches:
        return CallIntentVerification(False, "unknown_target")
    if len(matches) > 1:
        return CallIntentVerification(False, "ambiguous_target")
    index = matches[0]

    parameters = candidate_parameters(example.candidates[index])
    if parameters is not None:
        shape = shape_of_call(call, receiver=isinstance(call.func, ast.Attribute))
        if not candidate_bindable(parameters, (shape,)):
            return CallIntentVerification(False, "unbindable_call", target_index=index)

    try:
        expected = ast.parse(expected_repair_source(example))
        actual = ast.parse(apply_call_intent(example, call))
    except (SyntaxError, ValueError):
        return CallIntentVerification(False, "invalid_call_expression", target_index=index)

    if ast.dump(expected, include_attributes=False) == ast.dump(actual, include_attributes=False):
        return CallIntentVerification(True, "ok", target_index=index)
    if index != example.answer_index:
        return CallIntentVerification(False, "wrong_target", target_index=index)
    return CallIntentVerification(False, "wrong_arguments", target_index=index)


def feedback_for_call_intent(verification: CallIntentVerification) -> str:
    """Category-only feedback; never reveals the correct target or arguments."""
    messages = {
        "invalid_call_expression": (
            "The reply is not a single Python call expression. Reply with only "
            "the call, for example name(arg1, arg2)."
        ),
        "unknown_target": (
            "The callee is not one of the candidates. Call one of the candidate "
            "definitions by its exact name."
        ),
        "ambiguous_target": (
            "The callee name matches more than one candidate, so the call does "
            "not identify a single definition."
        ),
        "unbindable_call": (
            "The arguments cannot bind that candidate's signature. Match the "
            "original call site's arguments to the candidate's parameters."
        ),
        "wrong_target": (
            "The selected callee violates the repository constraint. Choose a "
            "different candidate."
        ),
        "wrong_arguments": (
            "The callee is acceptable but the arguments differ from the original "
            "call site. Preserve the original arguments exactly."
        ),
        "unsupported_task": "This task is not supported by the call-intent verifier.",
    }
    return messages.get(
        verification.reason,
        "The deterministic verifier rejected the call. Reply with only the call.",
    )


def build_call_intent_prompt(
    example: DecisionExample,
    *,
    recommendation_index: int | None = None,
    previous_output: str | None = None,
    feedback: str | None = None,
) -> str:
    """Prompt requesting only the replacement call expression."""
    if not eligible(example):
        raise ValueError("call-intent prompt expects a supported single-call-site example")
    if recommendation_index is not None and not (
        0 <= recommendation_index < len(example.candidates)
    ):
        raise ValueError("recommendation_index is out of range")

    nl = "\n"
    candidate_block = (nl + nl).join(
        f"Candidate {i + 1}:{nl}{c}" for i, c in enumerate(example.candidates)
    )
    sections = [
        f"The caller below contains one masked call, {MARKER}(...).",
        (
            "Reply with only the Python call expression that should replace it, "
            "naming one candidate and keeping the original arguments. Do not "
            "write a function or any other code."
        ),
        "Caller:" + nl + example.context,
        "Candidates:" + nl + candidate_block,
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
            "Reply with only the replacement call expression.",
        ])
    return (nl + nl).join(sections)


def run_call_intent_loop(
    example: DecisionExample,
    generate: Callable[[str], str],
    *,
    recommendation_index: int | None = None,
    max_attempts: int = 3,
) -> CallIntentOutcome:
    """Bounded generate, verify, category-feedback loop for call intents."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    attempts: list[CallIntentAttempt] = []
    previous_output: str | None = None
    feedback: str | None = None
    for _ in range(max_attempts):
        prompt = build_call_intent_prompt(
            example,
            recommendation_index=recommendation_index,
            previous_output=previous_output,
            feedback=feedback,
        )
        output = generate(prompt)
        verification = verify_call_intent(example, output)
        attempts.append(CallIntentAttempt(prompt, output, verification))
        if verification.valid:
            return CallIntentOutcome(True, tuple(attempts))
        previous_output = output
        feedback = feedback_for_call_intent(verification)
    return CallIntentOutcome(False, tuple(attempts))


def run_paired_call_intent(
    example: DecisionExample,
    generate_factory: Callable[[], Callable[[str], str]],
    *,
    recommendation_index: int,
    max_attempts: int = 3,
) -> PairedCallIntentOutcome:
    """Baseline vs assisted call-intent repair with fresh generator instances."""
    baseline = run_call_intent_loop(
        example, generate_factory(), recommendation_index=None, max_attempts=max_attempts
    )
    assisted = run_call_intent_loop(
        example,
        generate_factory(),
        recommendation_index=recommendation_index,
        max_attempts=max_attempts,
    )
    return PairedCallIntentOutcome(baseline=baseline, assisted=assisted)


def masked_call_source(example: DecisionExample) -> str | None:
    """Source text of the single masked call, for mocks and census."""
    if masked_call_count(example) != 1:
        return None
    tree = ast.parse(example.context)
    node = next(n for n in ast.walk(tree) if _is_marker_call(n))
    return ast.unparse(node)
