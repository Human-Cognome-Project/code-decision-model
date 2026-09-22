"""Tests for E034 closed-vocabulary argument operations."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from cdm.argument_ops import (
    InapplicableOperation,
    OperationPlan,
    apply_operations,
    argument_repair_example,
    argument_repair_examples,
    feedback_for_argument_repair,
    masked_call,
    parse_operation_plan,
    perturbations_for,
    predicate_search,
    run_argument_repair_loop,
    run_paired_argument_repair,
    verify_argument_repair,
)
from cdm.corrective import summarize_paired
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import repository_hard_masked_call_examples
from cdm.synthetic import DecisionExample


def _function_example() -> DecisionExample:
    return DecisionExample(
        context="def caller(value):\n    prepared = value.strip()\n    return __CALL_TARGET__(prepared, 3, strict=True)\n",
        question="q",
        candidates=(
            "normalize(value, depth, strict)\ndef normalize(value, depth=1, strict=False):\n    return value\n",
            "parse(value, depth, mode)\ndef parse(value, depth=1, mode=0):\n    return value\n",
            "emit(value, level, flag)\ndef emit(value, level=1, flag=False):\n    return value\n",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="repo::example.py",
    )


def _method_example() -> DecisionExample:
    return DecisionExample(
        context="def caller(self, value):\n    return self.__CALL_TARGET__(value, 2)\n",
        question="q",
        candidates=(
            "decode(self, value, width)\ndef decode(self, value, width=1):\n    return value\n",
            "clean(self, value, depth)\ndef clean(self, value, depth=1):\n    return value\n",
        ),
        answer_index=1,
        task="python.hard_masked_same_class_call",
        source="repo::example.py",
    )


def test_parse_is_strict_and_case_insensitive():
    assert parse_operation_plan("candidate 2", 4) == OperationPlan(1, ())
    assert parse_operation_plan("Candidate 1; Swap 1 2; drop mode", 4) == OperationPlan(
        0, (("swap", "1", "2"), ("drop", "mode"))
    )
    assert parse_operation_plan("```\ncandidate 3; rename a b; name 2 depth; unname flag; keep\n```", 4) is None
    assert parse_operation_plan("candidate 3; keep", 4) == OperationPlan(2, (("keep",),))
    for bad in ["", "3", "candidate 9", "candidate 1;", "candidate 1; swap 1", "candidate 1; explode 1",
                "normalize(prepared)", "candidate 1 because", "candidate 1; keep; keep"]:
        assert parse_operation_plan(bad, 4) is None, bad


def test_apply_operations_and_inapplicable_cases():
    call = masked_call(_function_example().context)
    assert ast.unparse(apply_operations(call, [("swap", "1", "2")])) == "__CALL_TARGET__(3, prepared, strict=True)"
    assert ast.unparse(apply_operations(call, [("drop", "strict")])) == "__CALL_TARGET__(prepared, 3)"
    assert ast.unparse(apply_operations(call, [("rename", "strict", "mode")])) == "__CALL_TARGET__(prepared, 3, mode=True)"
    assert ast.unparse(apply_operations(call, [("name", "2", "depth")])) == "__CALL_TARGET__(prepared, strict=True, depth=3)"
    assert ast.unparse(apply_operations(call, [("unname", "strict")])) == "__CALL_TARGET__(prepared, 3, True)"
    assert ast.unparse(apply_operations(call, [("keep",)])) == ast.unparse(call)
    for op in [("swap", "1", "1"), ("swap", "1", "5"), ("drop", "nope"), ("rename", "nope", "x"),
               ("rename", "strict", "strict"), ("name", "9", "depth"), ("name", "1", "strict"), ("unname", "nope")]:
        with pytest.raises(InapplicableOperation):
            apply_operations(call, [op])


def test_every_perturbation_is_restored_by_its_plan():
    for base in (_function_example(), _method_example()):
        options = perturbations_for(base)
        assert options
        for kind in options:
            item = argument_repair_example(base, kind=kind)
            assert item is not None and item.perturbation == kind
            assert "__CALL_TARGET__" in item.example.context
            assert item.example.context != base.context
            assert verify_argument_repair(item, item.restoring_plan.render()).valid, kind


def test_function_example_offers_all_four_perturbations():
    assert set(perturbations_for(_function_example())) == {"swap", "keywordize", "bogus_keyword", "rename_keyword"}


def test_verification_categories_in_order():
    item = argument_repair_example(_function_example(), kind="bogus_keyword")
    cases = {
        "banana": "invalid_plan",
        "candidate 1; drop nope": "inapplicable_operation",
        "candidate 1": "unbindable_call",          # bogus keyword still present
        "candidate 3; drop mode": "unbindable_call",  # emit lacks strict=
        "candidate 2; drop strict": "wrong_target",   # binds parse, wrong candidate
        "candidate 1; drop mode; swap 1 2": "wrong_operations",
        "candidate 1; drop mode": "ok",
    }
    for output, reason in cases.items():
        result = verify_argument_repair(item, output)
        assert result.reason == reason, (output, result)
        assert result.valid == (reason == "ok")


def test_feedback_never_reveals_target_or_plan():
    item = argument_repair_example(_function_example(), kind="rename_keyword")
    for output in ["banana", "candidate 2; keep", "candidate 1; keep", "candidate 1; drop nope"]:
        text = feedback_for_argument_repair(verify_argument_repair(item, output))
        assert "normalize" not in text and "candidate 1" not in text.lower()
        assert "strict" not in text and "mode" not in text


def test_deterministic_choice_by_seed_excludes_form_only_by_default():
    base = _function_example()
    a = argument_repair_example(base, seed=3)
    b = argument_repair_example(base, seed=3)
    assert a == b
    kinds = {argument_repair_example(base, seed=s).perturbation for s in range(12)}
    assert len(kinds) > 1
    assert "keywordize" not in kinds
    assert argument_repair_example(base, kind="keywordize") is not None
    with_form = {argument_repair_example(base, seed=s, include_form_only=True).perturbation for s in range(24)}
    assert "keywordize" in with_form


def test_no_perturbation_for_multi_site_or_starred_calls():
    base = _function_example()
    twice = DecisionExample(
        "def c(v):\n    a = __CALL_TARGET__(v, 1)\n    return __CALL_TARGET__(a, 2)\n",
        "q", base.candidates, 0, base.task, base.source,
    )
    starred = DecisionExample("def c(*v):\n    return __CALL_TARGET__(*v)\n", "q", base.candidates, 0, base.task, base.source)
    assert argument_repair_example(twice) is None
    assert argument_repair_example(starred) is None


def test_predicate_search_contains_restoring_plan_and_prunes():
    for kind in ("swap", "keywordize", "bogus_keyword", "rename_keyword"):
        item = argument_repair_example(_function_example(), kind=kind)
        plans = predicate_search(item)
        assert item.restoring_plan in plans, kind
        # Bindability alone must not be able to credit an unbindable candidate.
        assert all(verify_argument_repair(item, p.render()).reason != "unbindable_call" for p in plans)


def test_loop_and_paired_delta_feed_e026():
    item = argument_repair_example(_function_example(), kind="bogus_keyword")

    class Follower:
        def __init__(self):
            self.calls = 0

        def __call__(self, prompt):
            self.calls += 1
            if "candidate 1 is recommended" in prompt.lower():
                return "candidate 1; drop mode"
            return "candidate 2; drop mode" if self.calls == 1 else "candidate 1; drop mode"

    paired = run_paired_argument_repair(item, Follower, recommendation_index=0, max_attempts=3)
    assert paired.baseline.success and paired.baseline.correction_turns == 1
    assert paired.assisted.first_pass_success
    assert paired.correction_turn_delta == 1
    assert "Deterministic verifier feedback" in paired.baseline.attempts[1].prompt
    assert summarize_paired([paired]).correction_turn_deltas == (1,)

    stuck = run_argument_repair_loop(item, lambda _: "banana", max_attempts=2)
    assert not stuck.success and stuck.attempts_used == 2


def test_prompt_lists_call_site_facts_and_marks_recommendation_fallible():
    item = argument_repair_example(_function_example(), kind="keywordize")
    from cdm.argument_ops import build_argument_repair_prompt
    prompt = build_argument_repair_prompt(item, recommendation_index=2)
    assert "Positional arguments at the call site: 1." in prompt
    assert "Keyword arguments: strict, depth." in prompt
    assert "fallible" in prompt and "candidate 3 is recommended" in prompt
    with pytest.raises(ValueError):
        build_argument_repair_prompt(item, recommendation_index=7)


def test_repository_census_restoring_plans_always_verify():
    root = Path(__file__).resolve().parents[1]
    examples = [
        *repository_hard_masked_call_examples(root, candidate_count=4),
        *repository_hard_masked_method_call_examples(root, candidate_count=4),
    ]
    items = argument_repair_examples(examples, seed=0)
    assert items
    for item in items:
        assert verify_argument_repair(item, item.restoring_plan.render()).valid, (item.example.source, item.perturbation)
        assert item.restoring_plan in predicate_search(item)
