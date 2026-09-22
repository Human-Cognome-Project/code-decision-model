"""Tests for the hard-constraint interface."""
from __future__ import annotations

import torch

from cdm.constraints import (
    AllAllowed,
    ConstrainedDecision,
    RejectSubstring,
    RequireSubstring,
    apply_constraints,
)


def test_all_allowed_preserves_argmax():
    scores = torch.tensor([0.1, 2.0, 0.5])
    result = apply_constraints(
        scores,
        code_context="ctx",
        question="q",
        candidates=("a", "b", "c"),
        constraints=[AllAllowed()],
    )
    assert isinstance(result, ConstrainedDecision)
    assert result.escalate is False
    assert result.chosen_index == 1
    assert result.allowed == (True, True, True)
    assert torch.allclose(result.probabilities, torch.softmax(scores, dim=-1))


def test_require_substring_filters():
    scores = torch.tensor([3.0, 1.0, 2.0])
    result = apply_constraints(
        scores,
        code_context="ctx",
        question="q",
        candidates=(
            "def alpha(): pass",
            "def beta(): pass",
            "def alpha_helper(): pass",
        ),
        constraints=[RequireSubstring("alpha")],
    )
    assert result.allowed == (True, False, True)
    assert result.escalate is False
    assert result.chosen_index == 0  # highest surviving score
    assert result.reasons[1] != ""


def test_reject_substring_filters():
    scores = torch.tensor([1.0, 4.0, 2.0])
    result = apply_constraints(
        scores,
        code_context="ctx",
        question="q",
        candidates=("safe", "bad_thing", "also_safe"),
        constraints=[RejectSubstring("bad")],
    )
    assert result.allowed == (True, False, True)
    assert result.chosen_index == 2
    assert result.escalate is False


def test_all_rejected_escalates():
    scores = torch.tensor([5.0, 4.0, 3.0])
    result = apply_constraints(
        scores,
        code_context="ctx",
        question="q",
        candidates=("x", "y", "z"),
        constraints=[RequireSubstring("nonexistent")],
    )
    assert result.allowed == (False, False, False)
    assert result.escalate is True
    assert result.chosen_index is None
    assert torch.all(result.probabilities == 0)


def test_multiple_constraints_conjunction():
    scores = torch.tensor([1.0, 3.0, 2.0, 0.5])
    result = apply_constraints(
        scores,
        code_context="ctx",
        question="q",
        candidates=(
            "keep_me alpha",
            "drop_me alpha",
            "keep_me beta",
            "drop_me beta",
        ),
        constraints=[
            RequireSubstring("keep"),
            RejectSubstring("beta"),
        ],
    )
    assert result.allowed == (True, False, False, False)
    assert result.chosen_index == 0
    assert result.escalate is False


def test_no_constraints_preserves_distribution():
    scores = torch.tensor([0.25, -0.5, 1.5])
    result = apply_constraints(
        scores,
        code_context="ctx",
        question="q",
        candidates=("a", "b", "c"),
        constraints=[],
    )
    assert result.allowed == (True, True, True)
    assert result.escalate is False
    assert result.chosen_index == 2
    assert torch.allclose(result.probabilities, torch.softmax(scores, dim=-1))


def test_constraint_wrong_candidate_count_is_rejected():
    class BrokenConstraint:
        def check(self, code_context, question, candidates):
            from cdm.constraints import ConstraintResult
            return ConstraintResult(allowed=(True,))

    try:
        apply_constraints(
            torch.tensor([1.0, 2.0]),
            code_context="ctx",
            question="q",
            candidates=("a", "b"),
            constraints=[BrokenConstraint()],
        )
    except ValueError as exc:
        assert "wrong number" in str(exc)
    else:
        raise AssertionError("expected malformed constraint result validation")
