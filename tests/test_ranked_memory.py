"""Tests for E032 ranked feasible re-recommendation."""
from __future__ import annotations

import pytest
import torch

from cdm.binding import CallSiteBindable
from cdm.constraints import RejectSubstring
from cdm.ranked_memory import (
    constraint_mask,
    ranked_recommendation,
    ranking_from_scores,
    run_selection_loop_with_ranked_memory,
    validate_ranking,
)
from cdm.rejection_memory import run_selection_loop_with_rejection_memory
from cdm.structured_edit import build_selection_prompt, run_selection_loop
from cdm.synthetic import DecisionExample


def _example() -> DecisionExample:
    return DecisionExample(
        context="def caller(x):\n    return __CALL_TARGET__(x, mode=1)\n",
        question="pick",
        candidates=(
            "a(x, mode)\ndef a(x, mode=0): return x\n",
            "b(x, mode)\ndef b(x, mode=0): return x\n",
            "c(x, mode)\ndef c(x, mode=0): return x\n",
            "d(x, flag)\ndef d(x, flag=0): return x\n",  # cannot bind mode=
        ),
        answer_index=2,
        task="python.hard_masked_direct_call",
        source="repo::x.py",
    )


def _follower():
    """E028 behaviour: follow the recommendation; without one, pick the lowest eligible."""
    def generate(prompt: str) -> str:
        lower = prompt.lower()
        marker = "candidate "
        tag = " is recommended"
        if tag in lower:
            start = lower.rfind(marker, 0, lower.index(tag)) + len(marker)
            return lower[start:lower.index(tag)].strip()
        allowed_line = next(l for l in prompt.splitlines() if l.startswith("Reply with one candidate number from: ") or l.startswith("Reply with a single integer"))
        if "from:" in allowed_line:
            return allowed_line.split("from:")[1].split(".")[0].split(",")[0].strip()
        return "1"
    return generate


def test_ranking_helpers():
    assert ranking_from_scores([0.1, 2.0, 0.5, -1.0]) == (1, 2, 0, 3)
    assert ranking_from_scores(torch.tensor([1.0, 1.0, 0.0])) == (0, 1, 2)
    assert validate_ranking((2, 0, 1), 3) == (2, 0, 1)
    with pytest.raises(ValueError):
        validate_ranking((0, 0, 1), 3)
    with pytest.raises(ValueError):
        validate_ranking((0, 1), 3)


def test_constraint_mask_uses_e019_path_and_predicate():
    example = _example()
    mask = constraint_mask(example, (3, 0, 1, 2), [CallSiteBindable()])
    assert mask == (True, True, True, False)
    assert constraint_mask(example, (0, 1, 2, 3), []) == (True, True, True, True)
    assert constraint_mask(example, (0, 1, 2, 3), [RejectSubstring("def")]) == (False,) * 4


def test_ranked_recommendation_skips_vetoed_and_rejected():
    allowed = (True, True, True, False)
    assert ranked_recommendation((3, 0, 1, 2), allowed=allowed, rejected=()) == 0
    assert ranked_recommendation((3, 0, 1, 2), allowed=allowed, rejected=(0,)) == 1
    assert ranked_recommendation((3, 0, 1, 2), allowed=allowed, rejected=(0, 1, 2)) is None
    assert ranked_recommendation((0, 1), allowed=(False, False), rejected=()) is None


def test_first_prompt_equals_frozen_prompt_without_constraints():
    example = _example()
    seen: list[str] = []

    def generate(prompt: str) -> str:
        seen.append(prompt)
        return "3"

    trace = run_selection_loop_with_ranked_memory(
        example, generate, ranking=(1, 2, 0, 3), max_attempts=2
    )
    assert seen[0] == build_selection_prompt(example, recommendation_index=1)
    assert trace.recommendations == (1,)
    assert not trace.gated_at_turn_zero


def test_post_rejection_rerecommendation_recovers_where_e029_and_e027_do_not():
    example = _example()
    ranking = (0, 2, 1, 3)  # scorer's top pick is wrong; its second pick is right

    frozen = run_selection_loop(example, _follower(), recommendation_index=0, max_attempts=2)
    memory = run_selection_loop_with_rejection_memory(
        example, _follower(), recommendation_index=0, max_attempts=2
    )
    ranked = run_selection_loop_with_ranked_memory(
        example, _follower(), ranking=ranking, max_attempts=2
    )

    # Frozen loop: the discredited recommendation persists and is re-followed.
    assert not frozen.success
    assert [a.output for a in frozen.attempts] == ["1", "1"]
    # E029: recommendation removed; follower falls back to the lowest eligible number.
    assert not memory.outcome.success
    assert [a.output for a in memory.outcome.attempts] == ["1", "2"]
    # E032: next feasible ranked candidate is recommended and followed.
    assert ranked.outcome.success
    assert [a.output for a in ranked.outcome.attempts] == ["1", "3"]
    assert ranked.recommendations == (0, 2)
    assert ranked.rejected_indices == (0,)
    assert ranked.outcome.correction_turns == 1


def test_turn_zero_gating_by_predicate_prevents_a_wrong_first_choice():
    example = _example()
    ranking = (3, 2, 0, 1)  # scorer's top pick cannot bind the call site

    ungated = run_selection_loop_with_ranked_memory(
        example, _follower(), ranking=ranking, max_attempts=2
    )
    gated = run_selection_loop_with_ranked_memory(
        example, _follower(), ranking=ranking, constraints=[CallSiteBindable()], max_attempts=2
    )

    assert ungated.recommendations[0] == 3
    assert not ungated.outcome.first_pass_success
    assert gated.gated_at_turn_zero
    assert gated.recommendations == (2,)
    assert gated.outcome.first_pass_success
    assert gated.allowed == (True, True, True, False)


def test_no_feasible_candidate_means_no_recommendation():
    example = _example()
    seen: list[str] = []

    def generate(prompt: str) -> str:
        seen.append(prompt)
        return "3"

    trace = run_selection_loop_with_ranked_memory(
        example, generate, ranking=(0, 1, 2, 3), constraints=[RejectSubstring("def")], max_attempts=1
    )
    assert trace.recommendations == (None,)
    assert "recommended" not in seen[0].lower()
    assert trace.outcome.success  # the generator can still answer without evidence


def test_rejected_candidate_stays_excluded_from_rerecommendation():
    example = _example()
    outputs = iter(["1", "2", "3"])
    trace = run_selection_loop_with_ranked_memory(
        example, lambda _: next(outputs), ranking=(0, 1, 2, 3), max_attempts=3
    )
    assert trace.recommendations == (0, 1, 2)
    assert trace.rejected_indices == (0, 1)
    assert trace.outcome.success


def test_validation():
    example = _example()
    with pytest.raises(ValueError):
        run_selection_loop_with_ranked_memory(example, lambda _: "1", ranking=(0, 1, 2, 3), max_attempts=0)
    with pytest.raises(ValueError):
        run_selection_loop_with_ranked_memory(example, lambda _: "1", ranking=(0, 1, 2))
