"""E034 closed-vocabulary argument operations.

E033 asked the compact generator to write one call expression and it could not
reliably produce even that: bare symbols, partial signatures, and retained
placeholders dominated. E023 showed the same generator emits a candidate index
with perfect reliability. E034 keeps the whole output inside a closed
vocabulary:

    candidate <k>[; <op>]*

    keep                      no argument change
    swap <i> <j>              exchange positional arguments i and j (1-based)
    drop <name>               remove keyword argument <name>
    rename <old> <new>        rename keyword argument <old> to <new>
    name <i> <param>          turn positional argument i into <param>=...
    unname <name>             turn keyword <name>=... into the last positional

Every token is an index, an operation word, a keyword already present at the
call site, or a parameter name visible in a candidate signature. Nothing is
free-form.

To give the operations something to do, the masked call site is perturbed
deterministically in a way that is restorable from visible information, and the
original call is the machine-labelled truth. The E024 predicate checks the
result against the chosen candidate's real signature before any comparison, and
because the operation space is small it also provides a model-free baseline:
enumerate every single operation and keep the plans that bind.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import random
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from .binding import Parameters, candidate_bindable, candidate_parameters, shape_of_call
from .call_intent import masked_call_count
from .repair import candidate_symbol, expected_repair_source, extract_python
from .synthetic import DecisionExample

MARKER = "__CALL_TARGET__"
TASK = "python.hard_masked_argument_repair"
OPERATIONS = ("keep", "swap", "drop", "rename", "name", "unname")

_OP_PATTERNS = {
    "keep": re.compile(r"^keep$"),
    "swap": re.compile(r"^swap\s+(\d+)\s+(\d+)$"),
    "drop": re.compile(r"^drop\s+([A-Za-z_]\w*)$"),
    "rename": re.compile(r"^rename\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)$"),
    "name": re.compile(r"^name\s+(\d+)\s+([A-Za-z_]\w*)$"),
    "unname": re.compile(r"^unname\s+([A-Za-z_]\w*)$"),
}
_CANDIDATE = re.compile(r"^candidate\s+(\d+)$")


@dataclass(frozen=True)
class OperationPlan:
    candidate_index: int
    operations: tuple[tuple[str, ...], ...]

    def render(self) -> str:
        parts = [f"candidate {self.candidate_index + 1}"]
        parts.extend(" ".join(op) for op in self.operations)
        return "; ".join(parts)


@dataclass(frozen=True)
class ArgumentRepairExample:
    """A perturbed masked-call decision with its restoring plan."""

    example: DecisionExample
    """Perturbed caller as context; candidates and answer unchanged."""

    expected_repair: str
    """Normalized source of the unperturbed, resolved caller (E021)."""

    perturbation: str
    restoring_plan: OperationPlan


@dataclass(frozen=True)
class ArgumentRepairVerification:
    valid: bool
    reason: str
    candidate_index: int | None = None


@dataclass(frozen=True)
class ArgumentRepairAttempt:
    prompt: str
    output: str
    verification: ArgumentRepairVerification


@dataclass(frozen=True)
class ArgumentRepairOutcome:
    success: bool
    attempts: tuple[ArgumentRepairAttempt, ...]

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
class PairedArgumentRepairOutcome:
    baseline: ArgumentRepairOutcome
    assisted: ArgumentRepairOutcome

    @property
    def success_delta(self) -> int:
        return int(self.assisted.success) - int(self.baseline.success)

    @property
    def correction_turn_delta(self) -> int | None:
        if not (self.baseline.success and self.assisted.success):
            return None
        return self.baseline.correction_turns - self.assisted.correction_turns


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_operation_plan(text: str, n_candidates: int) -> OperationPlan | None:
    """Strict parse of ``candidate <k>[; op]*``; None on any deviation."""
    code = extract_python(text).strip().strip("`").strip().rstrip(".")
    if not code:
        return None
    parts = [part.strip().lower() for part in code.split(";")]
    head = _CANDIDATE.match(parts[0])
    if head is None:
        return None
    one_based = int(head.group(1))
    if not 1 <= one_based <= n_candidates:
        return None

    operations: list[tuple[str, ...]] = []
    for part in parts[1:]:
        if not part:
            return None
        matched = None
        for name, pattern in _OP_PATTERNS.items():
            m = pattern.match(part)
            if m is not None:
                matched = (name, *m.groups())
                break
        if matched is None:
            return None
        operations.append(matched)
    if operations.count(("keep",)) > 1 or (("keep",) in operations and len(operations) > 1):
        return None
    return OperationPlan(one_based - 1, tuple(operations))


# ---------------------------------------------------------------------------
# Call-site manipulation
# ---------------------------------------------------------------------------


def _is_marker_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == MARKER)
        or (isinstance(node.func, ast.Attribute) and node.func.attr == MARKER)
    )


def masked_call(context: str) -> ast.Call:
    tree = ast.parse(context)
    return next(node for node in ast.walk(tree) if _is_marker_call(node))


class InapplicableOperation(ValueError):
    pass


def apply_operations(call: ast.Call, operations: Iterable[tuple[str, ...]]) -> ast.Call:
    """Apply operations to a copy of the call; raise InapplicableOperation."""
    node = copy.deepcopy(call)
    for op in operations:
        kind = op[0]
        if kind == "keep":
            continue
        if kind == "swap":
            i, j = int(op[1]) - 1, int(op[2]) - 1
            if i == j or not (0 <= i < len(node.args)) or not (0 <= j < len(node.args)):
                raise InapplicableOperation("swap index out of range")
            if isinstance(node.args[i], ast.Starred) or isinstance(node.args[j], ast.Starred):
                raise InapplicableOperation("cannot swap starred arguments")
            node.args[i], node.args[j] = node.args[j], node.args[i]
        elif kind == "drop":
            before = len(node.keywords)
            node.keywords = [kw for kw in node.keywords if kw.arg != op[1]]
            if len(node.keywords) == before:
                raise InapplicableOperation("no such keyword to drop")
        elif kind == "rename":
            old, new = op[1], op[2]
            names = [kw.arg for kw in node.keywords]
            if old not in names or new in names or old == new:
                raise InapplicableOperation("rename source missing or target present")
            for kw in node.keywords:
                if kw.arg == old:
                    kw.arg = new
        elif kind == "name":
            i, param = int(op[1]) - 1, op[2]
            if not (0 <= i < len(node.args)) or isinstance(node.args[i], ast.Starred):
                raise InapplicableOperation("name index out of range")
            if param in [kw.arg for kw in node.keywords]:
                raise InapplicableOperation("keyword already present")
            value = node.args.pop(i)
            node.keywords.append(ast.keyword(arg=param, value=value))
        elif kind == "unname":
            matches = [kw for kw in node.keywords if kw.arg == op[1]]
            if not matches:
                raise InapplicableOperation("no such keyword to unname")
            kw = matches[0]
            node.keywords = [k for k in node.keywords if k is not kw]
            insert_at = len([a for a in node.args if not isinstance(a, ast.Starred)])
            node.args.insert(insert_at, kw.value)
        else:
            raise InapplicableOperation(f"unknown operation {kind}")
    return node


def _with_callee(call: ast.Call, symbol: str) -> ast.Call:
    node = copy.deepcopy(call)
    if isinstance(node.func, ast.Attribute):
        node.func.attr = symbol
    else:
        node.func = ast.Name(id=symbol, ctx=ast.Load())
    return node


class _SpliceCall(ast.NodeTransformer):
    def __init__(self, replacement: ast.Call) -> None:
        self.replacement = replacement

    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        if _is_marker_call(node):
            return ast.copy_location(copy.deepcopy(self.replacement), node)
        return node


def _splice(context: str, call: ast.Call) -> str:
    tree = _SpliceCall(call).visit(ast.parse(context))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _bound_parameters(candidate: str, call: ast.Call) -> tuple[Parameters | None, bool]:
    return candidate_parameters(candidate), isinstance(call.func, ast.Attribute)


# ---------------------------------------------------------------------------
# Deterministic perturbations
# ---------------------------------------------------------------------------


def _stable_rng(*parts: object) -> random.Random:
    payload = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(payload).digest()[:8], "big"))


def _target_positional_names(example: DecisionExample, call: ast.Call) -> tuple[str, ...]:
    """Positional-or-keyword parameter names of the target, receiver dropped for
    attribute calls under the bound reading."""
    params = candidate_parameters(example.candidates[example.answer_index])
    if params is None:
        return ()
    names = params.positional_only + params.positional_or_keyword
    if isinstance(call.func, ast.Attribute) and names:
        names = names[1:]
    # Positional-only parameters cannot be named.
    keywordable = set(params.positional_or_keyword)
    return tuple(n if n in keywordable else "" for n in names)


def _negative_parameter_names(example: DecisionExample) -> tuple[str, ...]:
    target = candidate_parameters(example.candidates[example.answer_index])
    taken = set()
    if target is not None:
        taken = set(target.positional_or_keyword) | set(target.keyword_only) | set(target.positional_only)
    names: list[str] = []
    for index, candidate in enumerate(example.candidates):
        if index == example.answer_index:
            continue
        params = candidate_parameters(candidate)
        if params is None:
            continue
        for name in params.positional_or_keyword + params.keyword_only:
            if name not in taken and name not in names and name not in {"self", "cls"}:
                names.append(name)
    return tuple(names)


def perturbations_for(example: DecisionExample) -> dict[str, tuple[ast.Call, OperationPlan]]:
    """Every applicable perturbation: perturbed call plus its restoring plan."""
    if masked_call_count(example) != 1:
        return {}
    call = masked_call(example.context)
    positional = [a for a in call.args if not isinstance(a, ast.Starred)]
    keyword_names = [kw.arg for kw in call.keywords if kw.arg is not None]
    if any(isinstance(a, ast.Starred) for a in call.args) or any(kw.arg is None for kw in call.keywords):
        return {}
    answer = example.answer_index
    result: dict[str, tuple[ast.Call, OperationPlan]] = {}

    if len(positional) >= 2:
        i, j = len(positional) - 2, len(positional) - 1
        swapped = apply_operations(call, [("swap", str(i + 1), str(j + 1))])
        if ast.dump(swapped) != ast.dump(call):
            result["swap"] = (swapped, OperationPlan(answer, ((("swap", str(i + 1), str(j + 1))),)))

    names = _target_positional_names(example, call)
    if positional:
        last = len(positional) - 1
        if last < len(names) and names[last] and names[last] not in keyword_names:
            keyworded = apply_operations(call, [("name", str(last + 1), names[last])])
            result["keywordize"] = (keyworded, OperationPlan(answer, (("unname", names[last]),)))

    bogus = _negative_parameter_names(example)
    if bogus and (positional or keyword_names):
        value = copy.deepcopy(positional[0] if positional else call.keywords[0].value)
        extra = copy.deepcopy(call)
        extra.keywords.append(ast.keyword(arg=bogus[0], value=value))
        result["bogus_keyword"] = (extra, OperationPlan(answer, (("drop", bogus[0]),)))

    if keyword_names and bogus:
        old = keyword_names[-1]
        renamed = apply_operations(call, [("rename", old, bogus[0])])
        result["rename_keyword"] = (renamed, OperationPlan(answer, (("rename", bogus[0], old),)))

    return result


SEMANTIC_PERTURBATIONS = ("swap", "bogus_keyword", "rename_keyword")
"""Perturbations that change what the call does: wrong order, or a TypeError.

``keywordize`` is excluded by default because ``f(x, 3)`` and ``f(x, depth=3)``
execute identically; restoring it is a form edit, not a repair.
"""


def argument_repair_example(
    example: DecisionExample,
    *,
    seed: int = 0,
    kind: str | None = None,
    include_form_only: bool = False,
) -> ArgumentRepairExample | None:
    """Perturb one masked-call decision deterministically; None if none applies."""
    options = perturbations_for(example)
    if not include_form_only and kind is None:
        options = {k: v for k, v in options.items() if k in SEMANTIC_PERTURBATIONS}
    if not options:
        return None
    if kind is not None:
        if kind not in options:
            return None
        chosen = kind
    else:
        chosen = _stable_rng(seed, "argument-ops", example.source, example.context).choice(
            sorted(options)
        )
    perturbed_call, plan = options[chosen]
    perturbed_context = _splice(example.context, perturbed_call)
    return ArgumentRepairExample(
        example=DecisionExample(
            context=perturbed_context,
            question=(
                "Which candidate should replace __CALL_TARGET__, and which "
                "argument operations restore the correct call?"
            ),
            candidates=example.candidates,
            answer_index=example.answer_index,
            task=TASK,
            source=example.source,
        ),
        expected_repair=expected_repair_source(example),
        perturbation=chosen,
        restoring_plan=plan,
    )


def argument_repair_examples(
    examples: Iterable[DecisionExample],
    *,
    seed: int = 0,
    include_form_only: bool = False,
) -> list[ArgumentRepairExample]:
    result = []
    for example in examples:
        item = argument_repair_example(example, seed=seed, include_form_only=include_form_only)
        if item is not None:
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _resolve(item: ArgumentRepairExample, plan: OperationPlan) -> tuple[ast.Call, str]:
    call = masked_call(item.example.context)
    edited = apply_operations(call, plan.operations)
    symbol = candidate_symbol(item.example.candidates[plan.candidate_index])
    return _with_callee(edited, symbol), symbol


def verify_argument_repair(item: ArgumentRepairExample, generated: str) -> ArgumentRepairVerification:
    """Parse, apply, bind-check, then compare with the unperturbed repair."""
    plan = parse_operation_plan(generated, len(item.example.candidates))
    if plan is None:
        return ArgumentRepairVerification(False, "invalid_plan")
    index = plan.candidate_index
    try:
        resolved, _ = _resolve(item, plan)
    except InapplicableOperation:
        return ArgumentRepairVerification(False, "inapplicable_operation", index)

    params = candidate_parameters(item.example.candidates[index])
    if params is not None:
        shape = shape_of_call(resolved, receiver=isinstance(resolved.func, ast.Attribute))
        if not candidate_bindable(params, (shape,)):
            return ArgumentRepairVerification(False, "unbindable_call", index)

    actual = ast.parse(_splice(item.example.context, resolved))
    expected = ast.parse(item.expected_repair)
    if ast.dump(actual, include_attributes=False) == ast.dump(expected, include_attributes=False):
        return ArgumentRepairVerification(True, "ok", index)
    if index != item.example.answer_index:
        return ArgumentRepairVerification(False, "wrong_target", index)
    return ArgumentRepairVerification(False, "wrong_operations", index)


def feedback_for_argument_repair(verification: ArgumentRepairVerification) -> str:
    messages = {
        "invalid_plan": (
            "The reply is not a valid plan. Reply with 'candidate <number>' "
            "followed by zero or more operations separated by semicolons."
        ),
        "inapplicable_operation": (
            "An operation refers to an argument position or keyword that does "
            "not exist at the call site."
        ),
        "unbindable_call": (
            "After the operations, the call cannot bind that candidate's "
            "signature. Match the candidate's parameters."
        ),
        "wrong_target": (
            "The selected candidate violates the repository constraint. Choose "
            "a different candidate."
        ),
        "wrong_operations": (
            "The candidate is acceptable but the argument operations do not "
            "restore the correct call."
        ),
    }
    return messages.get(verification.reason, "The deterministic verifier rejected the plan.")


# ---------------------------------------------------------------------------
# Prompt and loops
# ---------------------------------------------------------------------------


def build_argument_repair_prompt(
    item: ArgumentRepairExample,
    *,
    recommendation_index: int | None = None,
    previous_output: str | None = None,
    feedback: str | None = None,
) -> str:
    example = item.example
    if recommendation_index is not None and not (0 <= recommendation_index < len(example.candidates)):
        raise ValueError("recommendation_index is out of range")
    n = len(example.candidates)
    nl = "\n"
    candidate_block = (nl + nl).join(f"Candidate {i + 1}:{nl}{c}" for i, c in enumerate(example.candidates))
    call = masked_call(example.context)
    keywords = ", ".join(kw.arg for kw in call.keywords if kw.arg is not None) or "none"
    sections = [
        f"The caller below contains one masked call, {MARKER}(...), whose arguments may be wrong.",
        (
            f"Reply with one line: 'candidate <1-{n}>' followed by zero or more "
            "argument operations separated by semicolons. Operations: keep; "
            "swap <i> <j>; drop <keyword>; rename <old> <new>; name <i> <param>; "
            "unname <keyword>. Positions are 1-based. Do not write code."
        ),
        f"Positional arguments at the call site: {len(call.args)}. Keyword arguments: {keywords}.",
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
            "Reply with one plan line only.",
        ])
    return (nl + nl).join(sections)


def run_argument_repair_loop(
    item: ArgumentRepairExample,
    generate: Callable[[str], str],
    *,
    recommendation_index: int | None = None,
    max_attempts: int = 3,
) -> ArgumentRepairOutcome:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    attempts: list[ArgumentRepairAttempt] = []
    previous_output: str | None = None
    feedback: str | None = None
    for _ in range(max_attempts):
        prompt = build_argument_repair_prompt(
            item,
            recommendation_index=recommendation_index,
            previous_output=previous_output,
            feedback=feedback,
        )
        output = generate(prompt)
        verification = verify_argument_repair(item, output)
        attempts.append(ArgumentRepairAttempt(prompt, output, verification))
        if verification.valid:
            return ArgumentRepairOutcome(True, tuple(attempts))
        previous_output = output
        feedback = feedback_for_argument_repair(verification)
    return ArgumentRepairOutcome(False, tuple(attempts))


def run_paired_argument_repair(
    item: ArgumentRepairExample,
    generate_factory: Callable[[], Callable[[str], str]],
    *,
    recommendation_index: int,
    max_attempts: int = 3,
) -> PairedArgumentRepairOutcome:
    baseline = run_argument_repair_loop(
        item, generate_factory(), recommendation_index=None, max_attempts=max_attempts
    )
    assisted = run_argument_repair_loop(
        item, generate_factory(), recommendation_index=recommendation_index, max_attempts=max_attempts
    )
    return PairedArgumentRepairOutcome(baseline=baseline, assisted=assisted)


# ---------------------------------------------------------------------------
# Model-free predicate search baseline
# ---------------------------------------------------------------------------


def single_operation_vocabulary(item: ArgumentRepairExample, candidate_index: int) -> list[tuple[str, ...]]:
    """Every single operation expressible at the call site for one candidate."""
    call = masked_call(item.example.context)
    positional = len([a for a in call.args if not isinstance(a, ast.Starred)])
    keywords = [kw.arg for kw in call.keywords if kw.arg is not None]
    params = candidate_parameters(item.example.candidates[candidate_index])
    param_names: list[str] = []
    if params is not None:
        param_names = [n for n in params.positional_or_keyword + params.keyword_only if n not in {"self", "cls"}]

    ops: list[tuple[str, ...]] = [("keep",)]
    for i in range(positional):
        for j in range(i + 1, positional):
            ops.append(("swap", str(i + 1), str(j + 1)))
    for name in keywords:
        ops.append(("drop", name))
        ops.append(("unname", name))
        for new in param_names:
            if new not in keywords:
                ops.append(("rename", name, new))
    for i in range(positional):
        for param in param_names:
            if param not in keywords:
                ops.append(("name", str(i + 1), param))
    return ops


def predicate_search(item: ArgumentRepairExample) -> tuple[OperationPlan, ...]:
    """All single-operation plans that bind their candidate's signature."""
    binding: list[OperationPlan] = []
    for index in range(len(item.example.candidates)):
        params = candidate_parameters(item.example.candidates[index])
        for op in single_operation_vocabulary(item, index):
            plan = OperationPlan(index, (op,))
            try:
                resolved, _ = _resolve(item, plan)
            except InapplicableOperation:
                continue
            if params is None:
                binding.append(plan)
                continue
            shape = shape_of_call(resolved, receiver=isinstance(resolved.func, ast.Attribute))
            if candidate_bindable(params, (shape,)):
                binding.append(plan)
    return tuple(binding)
