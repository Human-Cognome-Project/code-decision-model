from dataclasses import dataclass, field

from cdm.corrections import (
    CorrectionTask,
    FirstCandidateSelector,
    ScoreSelector,
    ValidationResult,
    run_correction_episode,
    run_paired_correction,
)


TASK = CorrectionTask(
    task_id="example",
    context="def add(a, b): ...",
    question="Implement add correctly.",
)


@dataclass
class ScriptedGenerator:
    turns: tuple[tuple[str, ...], ...]
    seen_prior_lengths: list[int] = field(default_factory=list)

    def generate(self, task, turn, prior_attempts):
        self.seen_prior_lengths.append(len(prior_attempts))
        return self.turns[min(turn, len(self.turns) - 1)]


@dataclass(frozen=True)
class ExactValidator:
    expected: str

    def validate(self, task, candidate):
        ok = candidate == self.expected
        return ValidationResult(
            passed=ok,
            feedback="" if ok else "deterministic validation failed",
        )


def test_first_try_success_has_zero_correction_turns():
    episode = run_correction_episode(
        TASK,
        generator=ScriptedGenerator((("good", "bad"),)),
        selector=FirstCandidateSelector(),
        validator=ExactValidator("good"),
        max_turns=3,
    )

    assert episode.success is True
    assert episode.attempted_turns == 1
    assert episode.correction_turns == 0
    assert episode.generated_candidates == 2
    assert episode.validations == 1


def test_failed_initial_attempt_then_success_counts_one_correction():
    generator = ScriptedGenerator((("bad",), ("good",)))
    episode = run_correction_episode(
        TASK,
        generator=generator,
        selector=FirstCandidateSelector(),
        validator=ExactValidator("good"),
        max_turns=3,
    )

    assert episode.success is True
    assert episode.attempted_turns == 2
    assert episode.correction_turns == 1
    assert generator.seen_prior_lengths == [0, 1]
    assert episode.attempts[0].validation.feedback


def test_paired_selector_can_reduce_correction_turns():
    turns = (("bad", "good"), ("good", "bad"))

    result = run_paired_correction(
        TASK,
        generator_factory=lambda: ScriptedGenerator(turns),
        baseline_selector=FirstCandidateSelector(),
        assisted_selector=ScoreSelector(
            scorer=lambda task, candidates: [
                1.0 if candidate == "good" else 0.0
                for candidate in candidates
            ]
        ),
        validator=ExactValidator("good"),
        max_turns=3,
    )

    assert result.baseline.success is True
    assert result.assisted.success is True
    assert result.baseline.correction_turns == 1
    assert result.assisted.correction_turns == 0
    assert result.success_delta == 0
    assert result.correction_turn_delta == 1


def test_success_delta_handles_unresolved_baseline_without_fake_turn_delta():
    turns = (("bad", "good"),)

    result = run_paired_correction(
        TASK,
        generator_factory=lambda: ScriptedGenerator(turns),
        baseline_selector=FirstCandidateSelector(),
        assisted_selector=ScoreSelector(
            scorer=lambda task, candidates: [0.0, 1.0]
        ),
        validator=ExactValidator("good"),
        max_turns=1,
    )

    assert result.baseline.success is False
    assert result.assisted.success is True
    assert result.success_delta == 1
    assert result.correction_turn_delta is None


def test_exhausted_episode_reports_failure_separately_from_turn_count():
    episode = run_correction_episode(
        TASK,
        generator=ScriptedGenerator((("bad",),)),
        selector=FirstCandidateSelector(),
        validator=ExactValidator("good"),
        max_turns=3,
    )

    assert episode.success is False
    assert episode.attempted_turns == 3
    assert episode.correction_turns == 2


def test_invalid_selector_index_is_rejected():
    class BrokenSelector:
        def select(self, task, candidates, turn, prior_attempts):
            return len(candidates)

    try:
        run_correction_episode(
            TASK,
            generator=ScriptedGenerator((("a", "b"),)),
            selector=BrokenSelector(),
            validator=ExactValidator("a"),
        )
    except ValueError as exc:
        assert "invalid candidate index" in str(exc)
    else:
        raise AssertionError("expected selector-index validation")


def test_score_selector_rejects_wrong_score_count():
    selector = ScoreSelector(scorer=lambda task, candidates: [1.0])

    try:
        selector.select(TASK, ("a", "b"), 0, ())
    except ValueError as exc:
        assert "wrong number" in str(exc)
    else:
        raise AssertionError("expected score-count validation")
