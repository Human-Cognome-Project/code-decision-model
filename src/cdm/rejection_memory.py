"""E029 deterministic rejection memory for structured selection.

The frozen E027 loop tells the generator when a selected candidate is wrong, but
leaves that rejected candidate and any recommendation for it in the next prompt.
E029 turns the verifier result into a hard next-turn constraint: once rejected,
a candidate is removed from the visible choice set and cannot be accepted again.

The first prompt is intentionally delegated to E023's existing builder so first-
turn behavior is byte-for-byte identical to the frozen protocol.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .structured_edit import (
    SelectionAttempt,
    SelectionOutcome,
    SelectionVerification,
    build_selection_prompt,
    feedback_for_selection,
    parse_candidate_index,
    verify_selection,
)
from .synthetic import DecisionExample


@dataclass(frozen=True)
class RejectionMemoryTrace:
    outcome: SelectionOutcome
    rejected_indices: tuple[int, ...]


def _validate_rejected(example: DecisionExample, rejected: Iterable[int]) -> tuple[int, ...]:
    frozen = tuple(dict.fromkeys(rejected))
    if any(index < 0 or index >= len(example.candidates) for index in frozen):
        raise ValueError("rejected candidate index out of range")
    if len(frozen) >= len(example.candidates):
        raise ValueError("at least one candidate must remain eligible")
    return frozen


def build_rejection_memory_prompt(
    example: DecisionExample,
    *,
    recommendation_index: int | None = None,
    rejected_indices: Iterable[int] = (),
    previous_output: str | None = None,
    feedback: str | None = None,
) -> str:
    """Build a structured-selection prompt with rejected candidates removed.

    With no rejected candidates this returns the frozen E023 prompt exactly.
    Original candidate numbering is preserved after exclusions so the verifier's
    answer index and recorded recommendation index remain stable.
    """
    rejected = _validate_rejected(example, rejected_indices)
    if not rejected:
        return build_selection_prompt(
            example,
            recommendation_index=recommendation_index,
            previous_output=previous_output,
            feedback=feedback,
        )

    if recommendation_index is not None and not (
        0 <= recommendation_index < len(example.candidates)
    ):
        raise ValueError("recommendation_index is out of range")

    active = [i for i in range(len(example.candidates)) if i not in rejected]
    allowed = ", ".join(str(i + 1) for i in active)
    candidate_block = "\n\n".join(
        f"Candidate {i + 1}:\n{example.candidates[i]}" for i in active
    )
    sections = [
        "Select which candidate should replace __CALL_TARGET__ in the caller.",
        f"Reply with one candidate number from: {allowed}. Do not write code.",
        "Caller:\n" + example.context,
        "Candidates:\n" + candidate_block,
    ]
    if recommendation_index is not None and recommendation_index not in rejected:
        sections.append(
            "Repository decision evidence (fallible): "
            f"candidate {recommendation_index + 1} is recommended. "
            "Use this as evidence, but still verify it against the code."
        )
    if previous_output is not None and feedback is not None:
        removed = ", ".join(str(i + 1) for i in rejected)
        sections.extend([
            "Previous attempt:\n" + previous_output,
            "Deterministic verifier feedback:\n" + feedback,
            f"Rejected candidate numbers are no longer eligible: {removed}.",
            f"Reply with one candidate number from: {allowed}.",
        ])
    return "\n\n".join(sections)


def verify_selection_with_memory(
    example: DecisionExample,
    generated: str,
    *,
    rejected_indices: Iterable[int] = (),
) -> SelectionVerification:
    """Verify a selection while enforcing the hard rejected-candidate set."""
    rejected = _validate_rejected(example, rejected_indices)
    selected = parse_candidate_index(generated, len(example.candidates))
    if selected is None:
        return SelectionVerification(False, "unparseable_selection")
    if selected in rejected:
        return SelectionVerification(
            False,
            "rejected_candidate",
            selected_index=selected,
        )
    return verify_selection(example, generated)


def feedback_for_rejection_memory(verification: SelectionVerification) -> str:
    if verification.reason == "rejected_candidate":
        return (
            "That candidate was already rejected by the deterministic verifier "
            "and is no longer eligible."
        )
    return feedback_for_selection(verification)


def run_selection_loop_with_rejection_memory(
    example: DecisionExample,
    generate: Callable[[str], str],
    *,
    recommendation_index: int | None = None,
    max_attempts: int = 3,
) -> RejectionMemoryTrace:
    """Bounded structured-selection loop with deterministic rejection memory."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")

    attempts: list[SelectionAttempt] = []
    rejected: list[int] = []
    previous_output: str | None = None
    feedback: str | None = None

    for _ in range(max_attempts):
        prompt = build_rejection_memory_prompt(
            example,
            recommendation_index=recommendation_index,
            rejected_indices=rejected,
            previous_output=previous_output,
            feedback=feedback,
        )
        output = generate(prompt)
        verification = verify_selection_with_memory(
            example,
            output,
            rejected_indices=rejected,
        )
        attempts.append(
            SelectionAttempt(
                prompt=prompt,
                output=output,
                verification=verification,
            )
        )
        if verification.valid:
            return RejectionMemoryTrace(
                SelectionOutcome(True, tuple(attempts)),
                tuple(rejected),
            )

        if (
            verification.reason == "wrong_selection"
            and verification.selected_index is not None
            and verification.selected_index not in rejected
            and len(rejected) < len(example.candidates) - 1
        ):
            rejected.append(verification.selected_index)

        previous_output = output
        feedback = feedback_for_rejection_memory(verification)

    return RejectionMemoryTrace(
        SelectionOutcome(False, tuple(attempts)),
        tuple(rejected),
    )
