"""Paired corrective-turn evaluation harness.

This module measures the project's primary success criterion without implementing
an agent framework. A generator proposes one or more candidate artifacts per turn,
a selector chooses one candidate, and a deterministic validator decides whether
the chosen candidate satisfies the task.

Generation, selection, and validation stay behind small protocols so later
experiments can substitute a local code generator and the real decision model
without changing the measurement semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence


@dataclass(frozen=True)
class CorrectionTask:
    """One code-correction task presented to both experimental conditions."""

    task_id: str
    context: str
    question: str


@dataclass(frozen=True)
class ValidationResult:
    """Deterministic outcome for one selected candidate."""

    passed: bool
    feedback: str = ""


@dataclass(frozen=True)
class CorrectionAttempt:
    """One generated, selected, and validated turn."""

    turn: int
    candidates: tuple[str, ...]
    chosen_index: int
    validation: ValidationResult

    @property
    def chosen_candidate(self) -> str:
        return self.candidates[self.chosen_index]


@dataclass(frozen=True)
class CorrectionEpisode:
    """Complete outcome for one task under one selection condition."""

    task_id: str
    success: bool
    attempts: tuple[CorrectionAttempt, ...]
    max_turns: int

    @property
    def attempted_turns(self) -> int:
        return len(self.attempts)

    @property
    def correction_turns(self) -> int:
        """Number of regeneration turns after the initial proposal round."""
        return max(0, self.attempted_turns - 1)

    @property
    def generated_candidates(self) -> int:
        return sum(len(attempt.candidates) for attempt in self.attempts)

    @property
    def validations(self) -> int:
        return self.attempted_turns


@dataclass(frozen=True)
class PairedCorrectionResult:
    """Baseline and assisted outcomes for the same task."""

    baseline: CorrectionEpisode
    assisted: CorrectionEpisode

    def __post_init__(self) -> None:
        if self.baseline.task_id != self.assisted.task_id:
            raise ValueError("paired episodes must refer to the same task")

    @property
    def success_delta(self) -> int:
        """Positive when assistance resolves a task that baseline does not."""
        return int(self.assisted.success) - int(self.baseline.success)

    @property
    def correction_turn_delta(self) -> int | None:
        """Baseline minus assisted corrections when both conditions resolve."""
        if not (self.baseline.success and self.assisted.success):
            return None
        return self.baseline.correction_turns - self.assisted.correction_turns


class CandidateGenerator(Protocol):
    """Generate candidates for one correction turn."""

    def generate(
        self,
        task: CorrectionTask,
        turn: int,
        prior_attempts: Sequence[CorrectionAttempt],
    ) -> Sequence[str]:
        ...


class CandidateSelector(Protocol):
    """Choose one candidate index from a generated set."""

    def select(
        self,
        task: CorrectionTask,
        candidates: Sequence[str],
        turn: int,
        prior_attempts: Sequence[CorrectionAttempt],
    ) -> int:
        ...


class CandidateValidator(Protocol):
    """Deterministically validate the selected candidate."""

    def validate(
        self,
        task: CorrectionTask,
        candidate: str,
    ) -> ValidationResult:
        ...


@dataclass(frozen=True)
class FirstCandidateSelector:
    """Baseline selector: accept the generator's first candidate."""

    def select(
        self,
        task: CorrectionTask,
        candidates: Sequence[str],
        turn: int,
        prior_attempts: Sequence[CorrectionAttempt],
    ) -> int:
        return 0


@dataclass(frozen=True)
class ScoreSelector:
    """Choose the maximum score from an injected scoring function."""

    scorer: Callable[[CorrectionTask, Sequence[str]], Sequence[float]]

    def select(
        self,
        task: CorrectionTask,
        candidates: Sequence[str],
        turn: int,
        prior_attempts: Sequence[CorrectionAttempt],
    ) -> int:
        scores = tuple(float(value) for value in self.scorer(task, candidates))
        if len(scores) != len(candidates):
            raise ValueError("scorer returned wrong number of candidate scores")
        return max(range(len(scores)), key=scores.__getitem__)


def run_correction_episode(
    task: CorrectionTask,
    *,
    generator: CandidateGenerator,
    selector: CandidateSelector,
    validator: CandidateValidator,
    max_turns: int = 4,
) -> CorrectionEpisode:
    """Run one bounded generate, select, validate correction episode."""
    if max_turns < 1:
        raise ValueError("max_turns must be positive")

    attempts: list[CorrectionAttempt] = []

    for turn in range(max_turns):
        candidates = tuple(
            generator.generate(
                task,
                turn,
                tuple(attempts),
            )
        )
        if not candidates:
            raise ValueError("generator returned no candidates")

        chosen_index = int(
            selector.select(
                task,
                candidates,
                turn,
                tuple(attempts),
            )
        )
        if chosen_index < 0 or chosen_index >= len(candidates):
            raise ValueError(
                f"selector returned invalid candidate index {chosen_index} "
                f"for {len(candidates)} candidates"
            )

        validation = validator.validate(task, candidates[chosen_index])
        if not isinstance(validation, ValidationResult):
            raise TypeError("validator must return ValidationResult")

        attempt = CorrectionAttempt(
            turn=turn,
            candidates=candidates,
            chosen_index=chosen_index,
            validation=validation,
        )
        attempts.append(attempt)

        if validation.passed:
            return CorrectionEpisode(
                task_id=task.task_id,
                success=True,
                attempts=tuple(attempts),
                max_turns=max_turns,
            )

    return CorrectionEpisode(
        task_id=task.task_id,
        success=False,
        attempts=tuple(attempts),
        max_turns=max_turns,
    )


def run_paired_correction(
    task: CorrectionTask,
    *,
    generator_factory: Callable[[], CandidateGenerator],
    baseline_selector: CandidateSelector,
    assisted_selector: CandidateSelector,
    validator: CandidateValidator,
    max_turns: int = 4,
) -> PairedCorrectionResult:
    """Run baseline and assisted conditions from fresh generator instances."""
    baseline = run_correction_episode(
        task,
        generator=generator_factory(),
        selector=baseline_selector,
        validator=validator,
        max_turns=max_turns,
    )
    assisted = run_correction_episode(
        task,
        generator=generator_factory(),
        selector=assisted_selector,
        validator=validator,
        max_turns=max_turns,
    )
    return PairedCorrectionResult(
        baseline=baseline,
        assisted=assisted,
    )
