from __future__ import annotations

from cdm.rejection_memory import (
    build_rejection_memory_prompt,
    run_selection_loop_with_rejection_memory,
    verify_selection_with_memory,
)
from cdm.structured_edit import build_selection_prompt
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="def caller(x):\n    return __CALL_TARGET__(x)\n",
        question="pick",
        candidates=(
            "a(x)\ndef a(x): return x\n",
            "b(x)\ndef b(x): return x\n",
            "c(x)\ndef c(x): return x\n",
            "d(x)\ndef d(x): return x\n",
        ),
        answer_index=2,
        task="python.hard_masked_direct_call",
        source="repo::x.py",
    )


def test_first_prompt_is_exactly_frozen_prompt():
    example = _example()
    assert build_rejection_memory_prompt(
        example,
        recommendation_index=1,
    ) == build_selection_prompt(
        example,
        recommendation_index=1,
    )


def test_rejected_candidate_and_recommendation_are_removed():
    example = _example()
    prompt = build_rejection_memory_prompt(
        example,
        recommendation_index=1,
        rejected_indices=(1,),
        previous_output="2",
        feedback="wrong",
    )
    assert "Candidate 2:" not in prompt
    assert "b(x)" not in prompt
    assert "candidate 2 is recommended" not in prompt.lower()
    assert "1, 3, 4" in prompt
    assert "Rejected candidate numbers are no longer eligible: 2." in prompt


def test_original_numbering_is_preserved_after_removal():
    example = _example()
    prompt = build_rejection_memory_prompt(
        example,
        rejected_indices=(0, 1),
        previous_output="2",
        feedback="wrong",
    )
    assert "Candidate 3:" in prompt
    assert "Candidate 4:" in prompt
    assert "Candidate 1:" not in prompt
    assert "Candidate 2:" not in prompt


def test_verifier_refuses_a_rejected_candidate():
    example = _example()
    rejected = verify_selection_with_memory(
        example,
        "2",
        rejected_indices=(1,),
    )
    assert not rejected.valid
    assert rejected.reason == "rejected_candidate"
    assert rejected.selected_index == 1

    correct = verify_selection_with_memory(
        example,
        "3",
        rejected_indices=(1,),
    )
    assert correct.valid


def test_loop_turns_wrong_recommendation_into_hard_exclusion():
    example = _example()
    prompts: list[str] = []

    def generate(prompt: str) -> str:
        prompts.append(prompt)
        if len(prompts) == 1:
            return "2"  # follow the wrong recommendation
        # Candidate 2 is absent on the correction turn; choose the true target.
        assert "Candidate 2:" not in prompt
        return "3"

    trace = run_selection_loop_with_rejection_memory(
        example,
        generate,
        recommendation_index=1,
        max_attempts=2,
    )
    assert trace.outcome.success
    assert trace.outcome.attempts_used == 2
    assert trace.rejected_indices == (1,)


def test_correct_recommendation_is_unchanged_and_needs_no_memory():
    example = _example()

    def generate(prompt: str) -> str:
        assert "candidate 3 is recommended" in prompt.lower()
        return "3"

    trace = run_selection_loop_with_rejection_memory(
        example,
        generate,
        recommendation_index=2,
        max_attempts=2,
    )
    assert trace.outcome.first_pass_success
    assert trace.rejected_indices == ()
