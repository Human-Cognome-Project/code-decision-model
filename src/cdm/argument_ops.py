"""E034 closed-vocabulary argument operations.

E033 asked the compact generator to write one call expression and it could not
reliably produce even that: bare symbols, partial signatures, and retained
placeholders dominated. E023 showed the same generator emits a candidate index
with perfect reliability. E034 keeps the whole output inside a closed
vocabulary:

    candidate <k>; <op>

    keep                      no argument change
    swap <i> <j>              exchange positional arguments i and j (1-based)
    drop <name>               remove keyword argument <name>
    rename <old> <new>        rename keyword argument <old> to <new>
    name <i> <param>          turn positional argument i into <param>=...
    unname <name>             turn keyword <name>=... into the last positional

Exactly one operation per plan. Every identifier operand must belong to the
plan vocabulary: keyword names present at the call site plus parameter names
visible in *any* candidate signature. Out-of-vocabulary operands are rejected
before applicability or bindability is considered, so a ``**kwargs`` candidate
cannot launder an invented keyword through the binding predicate.

To give the operations something to do, the masked call site is perturbed
deterministically and the original call is the machine-labelled truth. The
default (semantic) perturbations are constructed without consulting the answer
label: the corrupted call is a function of the caller and the *set* of
candidates only, and :func:`corruption_is_label_invariant` checks that
property mechanically by relabelling the example. The E024 predicate checks the
result against the chosen candidate's real signature before any comparison,
and because the plan space is small it also provides a model-free baseline:
enumerate every plan the parser accepts and keep the ones that bind.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import random
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace

from .binding import candidate_bindable, candidate_parameters, shape_of_call
from .call_intent import masked_call_count
from .repair import candidate_symbol, expected_repair_source, extract_python
from .synthetic import DecisionExample

MARKER = "__CALL_TARGET__"
TASK = "python.hard_masked_argument_repair"
OPERATIONS = ("keep", "swap", "drop", "rename", "name", "unname")

SEMANTIC_PERTURBATIONS = ("swap", "bogus_keyword", "rename_keyword")
"""Perturbations that change what the call does and are built label-free.

``keywordize`` is excluded by default for two reasons: ``f(x, 3)`` and
``f(x, depth=3)`` execute identically, so restoring it is a form edit rather
than a repair; and its keyword is taken from the target's own signature, so the
visible corruption depends on the answer label. It stays opt-in and is
characterised separately.
"""

_OP_PATTERNS = {
    "keep": re.compile(r"^keep$"),
    "swap": re.compile(r"^swap\s+(\d+)\s+(\d+)$"),
    "drop": re.compile(r"^drop\s+([A-Za-z_]\w*)$"),
    "rename": re.compile(r"^rename\s+([A-Za-z_]\w*)\s+([A-Za-z_]\w*)$"),
    "name": re.compile(r"^name\s+(\d+)\s+([A-Za-z_]\w*)$"),
    "unname": re.compile(r"^unname\s+([A-Za-z_]\w*)$"),
}
_CANDIDATE = re.compile(r"^candidate\s+(\d+)$")
_RECEIVER_NAMES = frozenset({"self", "cls"})


@dataclass(frozen=True)
class OperationPlan:
    """One candidate choice plus exactly one argument operation."""

    candidate_index: int
    operations: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if len(self.operations) != 1:
            raise ValueError("an E034 plan carries exactly one operation")
        if self.operations[0][0] not in OPERATIONS:
            raise ValueError(f"unknown operation {self.operations[0][0]!r}")

    @property
    def operation(self) -> tuple[str, ...]:
        return self.operations[0]

    def render(self) -> str:
        return f"candidate {self.candidate_index + 1}; " + " ".join(self.operation)


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
# Parsing and vocabulary
# ---------------------------------------------------------------------------


def parse_operation_plan(text: str, n_candidates: int) -> OperationPlan | None:
    """Strict parse of ``candidate <k>; <op>``; None on any deviation.

    Exactly one operation is required (``keep`` is the explicit no-op). A swap
    is canonicalised to ascending positions; ``swap i i`` is malformed.
    """
    code = extract_python(text).strip().strip("`").strip().rstrip(".")
    if not code:
        return None
    parts = [part.strip().lower() for part in code.split(";")]
    if len(parts) != 2:
        return None
    head = _CANDIDATE.match(parts[0])
    if head is None:
        return None
    one_based = int(head.group(1))
    if not 1 <= one_based <= n_candidates:
        return None

    matched: tuple[str, ...] | None = None
    for name, pattern in _OP_PATTERNS.items():
        m = pattern.match(parts[1])
        if m is not None:
            matched = (name, *m.groups())
            break
    if matched is None:
        return None
    if matched[0] == "swap":
        i, j = int(matched[1]), int(matched[2])
        if i == j:
            return None
        matched = ("swap", str(min(i, j)), str(max(i, j)))
    return OperationPlan(one_based - 1, (matched,))


def _visible_parameter_names(example: DecisionExample) -> tuple[str, ...]:
    """Keyword-capable parameter names across *all* candidates, sorted.

    The answer label is never consulted; the result is a function of the
    candidate set only.
    """
    names: set[str] = set()
    for candidate in example.candidates:
        params = candidate_parameters(candidate)
        if params is None:
            continue
        names.update(params.positional_or_keyword)
        names.update(params.keyword_only)
    return tuple(sorted(names - _RECEIVER_NAMES))


def _call_site_keywords(call: ast.Call) -> tuple[str, ...]:
    return tuple(kw.arg for kw in call.keywords if kw.arg is not None)


def plan_vocabulary(example: DecisionExample) -> frozenset[str]:
    """Identifiers a plan may use: call-site keywords plus visible parameters."""
    names = set(_visible_parameter_names(example))
    if masked_call_count(example) == 1:
        names.update(_call_site_keywords(masked_call(example.context)))
    return frozenset(names)


def operands_in_vocabulary(plan: OperationPlan, vocabulary: frozenset[str]) -> bool:
    """True when every identifier operand of the plan is in the vocabulary."""
    op = plan.operation
    identifiers: tuple[str, ...]
    if op[0] in ("drop", "unname"):
        identifiers = (op[1],)
    elif op[0] == "rename":
        identifiers = (op[1], op[2])
    elif op[0] == "name":
        identifiers = (op[2],)
    else:
        identifiers = ()
    return all(identifier in vocabulary for identifier in identifiers)


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


# ---------------------------------------------------------------------------
# Deterministic perturbations
# ---------------------------------------------------------------------------


def _stable_rng(*parts: object) -> random.Random:
    payload = "\x1f".join(str(p) for p in parts).encode("utf-8")
    return random.Random(int.from_bytes(hashlib.sha256(payload).digest()[:8], "big"))


def _label_free_rng(purpose: str, seed: int, example: DecisionExample) -> random.Random:
    """RNG seeded by everything visible in the prompt and nothing hidden."""
    return _stable_rng(purpose, seed, example.source, example.context, *example.candidates)


def _keywordize_names(example: DecisionExample, call: ast.Call) -> tuple[str, ...]:
    """Keyword-capable positional parameter names of the *target*.

    Used only by the opt-in ``keywordize`` perturbation, which is therefore
    label-dependent by construction (see :data:`SEMANTIC_PERTURBATIONS`).
    """
    params = candidate_parameters(example.candidates[example.answer_index])
    if params is None:
        return ()
    names = params.positional_only + params.positional_or_keyword
    if isinstance(call.func, ast.Attribute) and names:
        names = names[1:]
    keywordable = set(params.positional_or_keyword)
    return tuple(n if n in keywordable else "" for n in names)


def perturbations_for(
    example: DecisionExample, *, seed: int = 0
) -> dict[str, tuple[ast.Call, OperationPlan]]:
    """Every applicable perturbation: perturbed call plus its restoring plan.

    The corrupted calls for the semantic perturbations depend only on the
    caller, the candidate set, and ``seed``. ``answer_index`` is read solely
    to fill in the restoring plan's candidate, which is never shown.
    """
    if masked_call_count(example) != 1:
        return {}
    call = masked_call(example.context)
    positional = [a for a in call.args if not isinstance(a, ast.Starred)]
    keyword_names = list(_call_site_keywords(call))
    if any(isinstance(a, ast.Starred) for a in call.args) or any(kw.arg is None for kw in call.keywords):
        return {}
    answer = example.answer_index
    result: dict[str, tuple[ast.Call, OperationPlan]] = {}

    if len(positional) >= 2:
        i, j = len(positional) - 2, len(positional) - 1
        swapped = apply_operations(call, [("swap", str(i + 1), str(j + 1))])
        if ast.dump(swapped) != ast.dump(call):
            result["swap"] = (swapped, OperationPlan(answer, (("swap", str(i + 1), str(j + 1)),)))

    # Spare names: visible parameters not already used as keywords here.
    spare = [n for n in _visible_parameter_names(example) if n not in keyword_names]

    if spare and (positional or keyword_names):
        bogus = _label_free_rng("bogus_keyword", seed, example).choice(spare)
        value = copy.deepcopy(positional[0] if positional else call.keywords[0].value)
        extra = copy.deepcopy(call)
        extra.keywords.append(ast.keyword(arg=bogus, value=value))
        result["bogus_keyword"] = (extra, OperationPlan(answer, (("drop", bogus),)))

    if keyword_names and spare:
        old = keyword_names[-1]
        new = _label_free_rng("rename_keyword", seed, example).choice(spare)
        renamed = apply_operations(call, [("rename", old, new)])
        result["rename_keyword"] = (renamed, OperationPlan(answer, (("rename", new, old),)))

    names = _keywordize_names(example, call)
    if positional:
        last = len(positional) - 1
        if last < len(names) and names[last] and names[last] not in keyword_names:
            keyworded = apply_operations(call, [("name", str(last + 1), names[last])])
            result["keywordize"] = (keyworded, OperationPlan(answer, (("unname", names[last]),)))

    return result


def visible_corruption(example: DecisionExample, kind: str, *, seed: int = 0) -> str | None:
    """The corrupted caller a generator would see for ``kind``; None if absent."""
    options = perturbations_for(example, seed=seed)
    if kind not in options:
        return None
    return _splice(example.context, options[kind][0])


def corruption_is_label_invariant(
    example: DecisionExample,
    *,
    kinds: Sequence[str] = SEMANTIC_PERTURBATIONS,
    seed: int = 0,
) -> bool:
    """Leakage control: relabel the answer and require identical corruptions.

    For every alternative ``answer_index`` and every requested perturbation
    kind, the visible corrupted caller (or its absence) must be byte-identical
    to the one produced under the true label.
    """
    reference = {kind: visible_corruption(example, kind, seed=seed) for kind in kinds}
    for other in range(len(example.candidates)):
        if other == example.answer_index:
            continue
        relabelled = replace(example, answer_index=other)
        for kind in kinds:
            if visible_corruption(relabelled, kind, seed=seed) != reference[kind]:
                return False
    return True


def argument_repair_example(
    example: DecisionExample,
    *,
    seed: int = 0,
    kind: str | None = None,
    include_form_only: bool = False,
) -> ArgumentRepairExample | None:
    """Perturb one masked-call decision deterministically; None if none applies."""
    options = perturbations_for(example, seed=seed)
    if not include_form_only and kind is None:
        options = {k: v for k, v in options.items() if k in SEMANTIC_PERTURBATIONS}
    if not options:
        return None
    if kind is not None:
        if kind not in options:
            return None
        chosen = kind
    else:
        chosen = _label_free_rng("argument-ops", seed, example).choice(sorted(options))
    perturbed_call, plan = options[chosen]
    perturbed_context = _splice(example.context, perturbed_call)
    return ArgumentRepairExample(
        example=DecisionExample(
            context=perturbed_context,
            question=(
                "Which candidate should replace __CALL_TARGET__, and which "
                "argument operation restores the correct call?"
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


def _binds_candidate(item: ArgumentRepairExample, plan: OperationPlan, resolved: ast.Call) -> bool:
    params = candidate_parameters(item.example.candidates[plan.candidate_index])
    if params is None:
        return True
    shape = shape_of_call(resolved, receiver=isinstance(resolved.func, ast.Attribute))
    return candidate_bindable(params, (shape,))


def verify_argument_repair(item: ArgumentRepairExample, generated: str) -> ArgumentRepairVerification:
    """Parse and vocabulary-check, apply, bind-check, then compare with truth."""
    plan = parse_operation_plan(generated, len(item.example.candidates))
    if plan is None or not operands_in_vocabulary(plan, plan_vocabulary(item.example)):
        return ArgumentRepairVerification(False, "invalid_plan")
    index = plan.candidate_index
    try:
        resolved, _ = _resolve(item, plan)
    except InapplicableOperation:
        return ArgumentRepairVerification(False, "inapplicable_operation", index)

    if not _binds_candidate(item, plan, resolved):
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
            "The reply is not a valid plan. Reply with 'candidate <number>; "
            "<operation>' using exactly one operation, and only keyword and "
            "parameter names that appear in the call site or the candidates."
        ),
        "inapplicable_operation": (
            "The operation refers to an argument position or keyword that does "
            "not exist at the call site."
        ),
        "unbindable_call": (
            "After the operation, the call cannot bind that candidate's "
            "signature. Match the candidate's parameters."
        ),
        "wrong_target": (
            "The selected candidate violates the repository constraint. Choose "
            "a different candidate."
        ),
        "wrong_operations": (
            "The candidate is acceptable but the argument operation does not "
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
    keywords = ", ".join(_call_site_keywords(call)) or "none"
    allowed = ", ".join(sorted(plan_vocabulary(example))) or "none"
    sections = [
        f"The caller below contains one masked call, {MARKER}(...), whose arguments may be wrong.",
        (
            f"Reply with one line: 'candidate <1-{n}>; <operation>' with exactly "
            "one operation. Operations: keep; swap <i> <j>; drop <keyword>; "
            "rename <old> <new>; name <i> <param>; unname <keyword>. Positions "
            "are 1-based. Names must come from the allowed list. Do not write code."
        ),
        f"Positional arguments at the call site: {len(call.args)}. Keyword arguments: {keywords}.",
        f"Allowed names: {allowed}.",
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


def plan_space(item: ArgumentRepairExample) -> tuple[OperationPlan, ...]:
    """Every plan the verifier would carry past its first two gates.

    This is exactly the set of plans that parse, use only vocabulary operands,
    and apply at the call site: the generator's allowed action space, before
    bindability. Candidate choice is independent of the operation, so the space
    is candidates x operations.
    """
    call = masked_call(item.example.context)
    positional = len([a for a in call.args if not isinstance(a, ast.Starred)])
    keywords = list(_call_site_keywords(call))
    vocabulary = sorted(plan_vocabulary(item.example))
    unused = [n for n in vocabulary if n not in keywords]

    ops: list[tuple[str, ...]] = [("keep",)]
    for i in range(positional):
        for j in range(i + 1, positional):
            ops.append(("swap", str(i + 1), str(j + 1)))
    for name in keywords:
        ops.append(("drop", name))
        ops.append(("unname", name))
        for new in unused:
            ops.append(("rename", name, new))
    for i in range(positional):
        for param in unused:
            ops.append(("name", str(i + 1), param))
    return tuple(
        OperationPlan(index, (op,))
        for index in range(len(item.example.candidates))
        for op in ops
    )


def predicate_search(item: ArgumentRepairExample) -> tuple[OperationPlan, ...]:
    """All plans in :func:`plan_space` that bind their candidate's signature."""
    binding: list[OperationPlan] = []
    for plan in plan_space(item):
        try:
            resolved, _ = _resolve(item, plan)
        except InapplicableOperation:  # pragma: no cover - plan_space is applicable by construction
            continue
        if _binds_candidate(item, plan, resolved):
            binding.append(plan)
    return tuple(binding)


@dataclass(frozen=True)
class PredicateCensus:
    """What E024 bindability alone leaves of the plan space for one decision."""

    plan_space_size: int
    binding_plans: int
    surviving_candidates: int
    """Candidates with at least one binding plan."""

    restoring_plan_binds: bool
    solved_by_predicate: bool
    """The restoring plan is the only binding plan."""

    pure_selection: bool
    """Every candidate has exactly one binding plan, so only the target is open."""

    at_most_one_per_survivor: bool
    """No surviving candidate has more than one binding plan (weaker)."""


def predicate_census(item: ArgumentRepairExample) -> PredicateCensus:
    space = plan_space(item)
    plans = predicate_search(item)
    n = len(item.example.candidates)
    counts = [0] * n
    for plan in plans:
        counts[plan.candidate_index] += 1
    survivors = sum(c > 0 for c in counts)
    return PredicateCensus(
        plan_space_size=len(space),
        binding_plans=len(plans),
        surviving_candidates=survivors,
        restoring_plan_binds=item.restoring_plan in plans,
        solved_by_predicate=len(plans) == 1 and plans[0] == item.restoring_plan,
        pure_selection=all(c == 1 for c in counts),
        at_most_one_per_survivor=survivors > 0 and all(c <= 1 for c in counts),
    )
