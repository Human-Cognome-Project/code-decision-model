"""E023 structured-edit corrective-turn harness.

Removes full-function generation. The generator emits only a candidate index;
deterministic code applies the edit and the machine-labelled target judges it.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .repair import candidate_symbol
from .synthetic import DecisionExample

_SUPPORTED_TASKS = frozenset({
    "python.hard_masked_direct_call",
    "python.hard_masked_same_class_call",
})

# Accept only a structured selection such as "3", "candidate 3", or "Candidate 3:".
_INDEX_PATTERN = re.compile(
    r"(?:candidate\\s*)?(\\d+)\\s*(?:[:.\\)]?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SelectionVerification:
    """Whether a structured selection matched the machine label."""

    valid: bool
    reason: str
    selected_index: int | None = None


@dataclass(frozen=True)
class SelectionAttempt:
    prompt: str
    output: str
    verification: SelectionVerification


@dataclass(frozen=True)
class SelectionOutcome:
    success: bool
    attempts: tuple[SelectionAttempt, ...]

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
class PairedSelectionOutcome:
    baseline: SelectionOutcome
    assisted: SelectionOutcome

    @property
    def success_delta(self) -> int:
        return int(self.assisted.success) - int(self.baseline.success)

    @property
    def correction_turn_delta(self) -> int | None:
        if not (self.baseline.success and self.assisted.success):
            return None
        return self.baseline.correction_turns - self.assisted.correction_turns


def parse_candidate_index(text: str, n_candidates: int) -> int | None:
    """Parse a 0-based candidate index from structured generator output.

    Expects a 1-based index in the first matching token. Returns None when no
    legal index is present.
    """
    if n_candidates < 1:
        raise ValueError("n_candidates must be positive")
    stripped = text.strip()
    # Prefer a lone integer line.
    if stripped.isdigit():
        one_based = int(stripped)
        if 1 <= one_based <= n_candidates:
            return one_based - 1
        return None
    match = _INDEX_PATTERN.fullmatch(stripped)
    if match is None:
        return None
    one_based = int(match.group(1))
    if 1 <= one_based <= n_candidates:
        return one_based - 1
    return None


def apply_structured_edit(example: DecisionExample, selected_index: int) -> str:
    """Replace the masked call target with the selected candidate symbol."""
    if not 0 <= selected_index < len(example.candidates):
        raise ValueError("selected_index out of range")
    symbol = candidate_symbol(example.candidates[selected_index])
    if "__CALL_TARGET__" not in example.context:
        raise ValueError("example context has no __CALL_TARGET__ marker")
    return example.context.replace("__CALL_TARGET__", symbol)


def verify_selection(
    example: DecisionExample,
    generated: str,
) -> SelectionVerification:
    """Judge structured output against the machine-labelled answer index."""
    if example.task not in _SUPPORTED_TASKS:
        return SelectionVerification(False, "unsupported_task")

    selected = parse_candidate_index(generated, len(example.candidates))
    if selected is None:
        return SelectionVerification(False, "unparseable_selection")
    if selected != example.answer_index:
        return SelectionVerification(
            False,
            "wrong_selection",
            selected_index=selected,
        )
    return SelectionVerification(True, "ok", selected_index=selected)


def feedback_for_selection(verification: SelectionVerification) -> str:
    """Category-only feedback; never reveals the correct index."""
    messages = {
        "unparseable_selection": (
            "Could not parse a candidate index. Reply with a single integer "
            "from 1 to N naming the chosen candidate."
        ),
        "wrong_selection": (
            "The selected candidate violates the repository constraint. "
            "Choose a different candidate index."
        ),
        "unsupported_task": "This task is not supported by the structured-edit verifier.",
    }
    return messages.get(
        verification.reason,
        "The selection was rejected. Reply with a single candidate index.",
    )


def build_selection_prompt(
    example: DecisionExample,
    *,
    recommendation_index: int | None = None,
    previous_output: str | None = None,
    feedback: str | None = None,
) -> str:
    """Prompt that requests only a candidate index, not full function text."""
    if example.task not in _SUPPORTED_TASKS:
        raise ValueError("selection prompt expects a hard masked-call example")
    if recommendation_index is not None and not (
        0 <= recommendation_index < len(example.candidates)
    ):
        raise ValueError("recommendation_index is out of range")

    n = len(example.candidates)
    nl = "\n"
    candidate_block = (nl + nl).join(
        f"Candidate {i + 1}:{nl}{c}" for i, c in enumerate(example.candidates)
    )
    sections = [
        "Select which candidate should replace __CALL_TARGET__ in the caller.",
        f"Reply with a single integer from 1 to {n} only. Do not write code.",
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
            f"Reply with a single integer from 1 to {n} only.",
        ])
    return (nl + nl).join(sections)


def run_selection_loop(
    example: DecisionExample,
    generate: Callable[[str], str],
    *,
    recommendation_index: int | None = None,
    max_attempts: int = 3,
) -> SelectionOutcome:
    """Bounded select \u2192 verify \u2192 feedback loop."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    attempts: list[SelectionAttempt] = []
    previous_output: str | None = None
    feedback: str | None = None

    for _ in range(max_attempts):
        prompt = build_selection_prompt(
            example,
            recommendation_index=recommendation_index,
            previous_output=previous_output,
            feedback=feedback,
        )
        output = generate(prompt)
        verification = verify_selection(example, output)
        attempts.append(
            SelectionAttempt(
                prompt=prompt,
                output=output,
                verification=verification,
            )
        )
        if verification.valid:
            return SelectionOutcome(True, tuple(attempts))
        previous_output = output
        feedback = feedback_for_selection(verification)

    return SelectionOutcome(False, tuple(attempts))


def run_paired_selection(
    example: DecisionExample,
    generate_factory: Callable[[], Callable[[str], str]],
    *,
    recommendation_index: int,
    max_attempts: int = 3,
) -> PairedSelectionOutcome:
    """Baseline vs assisted structured selection with fresh generator instances."""
    baseline = run_selection_loop(
        example,
        generate_factory(),
        recommendation_index=None,
        max_attempts=max_attempts,
    )
    assisted = run_selection_loop(
        example,
        generate_factory(),
        recommendation_index=recommendation_index,
        max_attempts=max_attempts,
    )
    return PairedSelectionOutcome(baseline=baseline, assisted=assisted)
