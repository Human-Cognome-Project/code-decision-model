"""Tests for E034 closed-vocabulary argument operations."""
from __future__ import annotations

import ast
import itertools
from dataclasses import replace
from pathlib import Path

import pytest

from cdm.argument_ops import (
    SEMANTIC_PERTURBATIONS,
    InapplicableOperation,
    OperationPlan,
    apply_operations,
    argument_repair_example,
    argument_repair_examples,
    build_argument_repair_prompt,
    corruption_is_label_invariant,
    feedback_for_argument_repair,
    masked_call,
    parse_operation_plan,
    perturbations_for,
    plan_space,
    plan_vocabulary,
    predicate_census,
    predicate_search,
    run_argument_repair_loop,
    run_paired_argument_repair,
    verify_argument_repair,
    visible_corruption,
)
from cdm.corrective import summarize_paired
from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import repository_hard_masked_call_examples
from cdm.synthetic import DecisionExample


def _function_example() -> DecisionExample:
    # Candidate 2 accepts **options so an invented keyword would bind it: the
    # vocabulary gate, not bindability, must be what rejects such plans.
    return DecisionExample(
        context="def caller(value):\n    prepared = value.strip()\n    return __CALL_TARGET__(prepared, 3, strict=True)\n",
        question="q",
        candidates=(
            "normalize(value, depth, strict)\ndef normalize(value, depth=1, strict=False):\n    return value\n",
            "parse(value, depth, **options)\ndef parse(value, depth=1, **options):\n    return value\n",
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


def _repository_examples() -> list[DecisionExample]:
    root = Path(__file__).resolve().parents[1]
    return [
        *repository_hard_masked_call_examples(root, candidate_count=4),
        *repository_hard_masked_method_call_examples(root, candidate_count=4),
        *repository_hard_masked_cross_file_call_examples(root, candidate_count=4),
    ]


def test_parse_requires_exactly_one_operation_and_is_case_insensitive():
    assert parse_operation_plan("Candidate 1; Swap 2 1", 4) == OperationPlan(0, (("swap", "1", "2"),))
    assert parse_operation_plan("candidate 3; keep", 4) == OperationPlan(2, (("keep",),))
    assert parse_operation_plan("```\ncandidate 2; name 1 depth\n```", 4) == OperationPlan(1, (("name", "1", "depth"),))
    for bad in ["", "3", "candidate 2", "candidate 9; keep", "candidate 1;", "candidate 1; swap 1",
                "candidate 1; swap 1 1", "candidate 1; explode 1", "normalize(prepared)",
                "candidate 1 because", "candidate 1; keep; keep", "candidate 1; swap 1 2; drop mode",
                "candidate 1; rename a b; name 2 depth"]:
        assert parse_operation_plan(bad, 4) is None, bad
    with pytest.raises(ValueError):
        OperationPlan(0, ())
    with pytest.raises(ValueError):
        OperationPlan(0, (("keep",), ("keep",)))


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


# --- Finding 1: label-dependent perturbation leakage ------------------------


def test_semantic_corruptions_are_label_invariant_and_keywordize_is_not():
    base = _function_example()
    assert corruption_is_label_invariant(base)
    assert corruption_is_label_invariant(_method_example())
    # The control has teeth: keywordize names the target's own parameter.
    assert not corruption_is_label_invariant(base, kinds=("keywordize",))
    assert visible_corruption(base, "keywordize") != visible_corruption(replace(base, answer_index=2), "keywordize")


def test_bogus_names_are_drawn_from_the_label_free_union_of_candidates():
    base = _function_example()
    vocabulary = {"depth", "flag", "level", "strict", "value"}
    assert plan_vocabulary(base) == frozenset(vocabulary)
    for seed in range(8):
        for kind, op in (("bogus_keyword", "drop"), ("rename_keyword", "rename")):
            item = argument_repair_example(base, kind=kind, seed=seed)
            name = item.restoring_plan.operation[1]
            assert item.restoring_plan.operation[0] == op
            assert name in vocabulary - {"strict"}, (kind, seed, name)
    # Different seeds vary the chosen name; nothing about the target is preferred.
    names = {argument_repair_example(base, kind="bogus_keyword", seed=s).restoring_plan.operation[1] for s in range(16)}
    assert len(names) > 1
    assert names & {"level", "flag"} and names & {"depth", "value"}


def test_repository_corpora_pass_the_leakage_control():
    examples = _repository_examples()
    assert examples
    for example in examples:
        assert corruption_is_label_invariant(example), example.source


# --- Finding 2: closed vocabulary --------------------------------------------


def test_out_of_vocabulary_operands_are_invalid_even_when_they_would_bind():
    item = argument_repair_example(_function_example(), kind="swap")
    # Candidate 2 has **options: 'banana=' would bind, so only the vocabulary gate can reject it.
    for output in ["candidate 2; name 1 banana", "candidate 2; rename strict banana",
                   "candidate 1; name 1 banana", "candidate 1; rename strict banana",
                   "candidate 2; drop banana", "candidate 2; unname banana"]:
        assert verify_argument_repair(item, output).reason == "invalid_plan", output
    # The same shapes with in-vocabulary names get past the gate.
    assert verify_argument_repair(item, "candidate 2; name 1 level").reason in ("wrong_target", "unbindable_call")
    assert verify_argument_repair(item, "candidate 2; rename strict level").reason == "wrong_target"


# --- Verification order -------------------------------------------------------


def test_verification_categories_in_order():
    item = argument_repair_example(_function_example(), kind="bogus_keyword")
    bogus = item.restoring_plan.operation[1]
    unused = next(n for n in sorted(plan_vocabulary(item.example)) if n not in {bogus, "strict"})
    cases = {
        "banana": "invalid_plan",
        "candidate 1": "invalid_plan",                       # no operation
        f"candidate 1; drop {bogus}; keep": "invalid_plan",  # two operations
        "candidate 1; name 1 banana": "invalid_plan",        # out of vocabulary
        f"candidate 1; drop {unused}": "inapplicable_operation",
        "candidate 1; keep": "unbindable_call",              # bogus keyword still present
        f"candidate 3; drop {bogus}": "unbindable_call",     # emit lacks strict=
        f"candidate 2; drop {bogus}": "wrong_target",        # parse binds via **options
        "candidate 1; drop strict": "unbindable_call" if bogus in {"flag", "level"} else "wrong_operations",
        f"candidate 1; drop {bogus}": "ok",
    }
    for output, reason in cases.items():
        result = verify_argument_repair(item, output)
        assert result.reason == reason, (output, result)
        assert result.valid == (reason == "ok")


def test_feedback_never_reveals_target_or_plan():
    item = argument_repair_example(_function_example(), kind="rename_keyword")
    bogus = item.restoring_plan.operation[1]
    for output in ["banana", "candidate 2; keep", "candidate 1; keep", f"candidate 1; drop {bogus}"]:
        text = feedback_for_argument_repair(verify_argument_repair(item, output))
        assert "normalize" not in text and "candidate 1" not in text.lower()
        assert "strict" not in text and bogus not in text


def test_deterministic_choice_by_seed_excludes_form_only_by_default():
    base = _function_example()
    a = argument_repair_example(base, seed=3)
    b = argument_repair_example(base, seed=3)
    assert a == b
    kinds = {argument_repair_example(base, seed=s).perturbation for s in range(12)}
    assert len(kinds) > 1
    assert kinds <= set(SEMANTIC_PERTURBATIONS)
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


# --- Finding 3: baseline covers exactly the model's allowed plan space --------


def test_plan_space_equals_what_the_verifier_admits():
    for kind in ("swap", "bogus_keyword", "rename_keyword", "keywordize"):
        item = argument_repair_example(_function_example(), kind=kind)
        space = set(plan_space(item))
        assert len(space) == len(plan_space(item))
        n = len(item.example.candidates)
        positions = [str(i) for i in range(1, len(masked_call(item.example.context).args) + 2)]
        names = sorted(plan_vocabulary(item.example)) + ["banana"]
        ops = ["keep"]
        ops += [f"swap {i} {j}" for i in positions for j in positions]
        ops += [f"{w} {a}" for w in ("drop", "unname") for a in names]
        ops += [f"rename {a} {b}" for a in names for b in names]
        ops += [f"name {i} {a}" for i in positions for a in names]
        admitted = 0
        for k, op in itertools.product(range(1, n + 2), ops):
            text = f"candidate {k}; {op}"
            reason = verify_argument_repair(item, text).reason
            passes = reason not in ("invalid_plan", "inapplicable_operation")
            plan = parse_operation_plan(text, n)
            assert passes == (plan is not None and plan in space), (kind, text, reason)
            admitted += passes and text == plan.render()
        # Every plan in the space was reached by its own canonical rendering.
        assert admitted == len(space), kind


def test_predicate_search_contains_restoring_plan_and_prunes():
    for kind in ("swap", "keywordize", "bogus_keyword", "rename_keyword"):
        item = argument_repair_example(_function_example(), kind=kind)
        plans = predicate_search(item)
        assert item.restoring_plan in plans, kind
        assert set(plans) <= set(plan_space(item))
        # Bindability alone must not be able to credit an unbindable candidate.
        assert all(verify_argument_repair(item, p.render()).reason != "unbindable_call" for p in plans)


# --- Finding 4: census metric -------------------------------------------------


def test_predicate_census_distinguishes_pure_selection_from_survivor_count():
    base = _function_example()
    item = argument_repair_example(base, kind="swap")
    census = predicate_census(item)
    assert census.plan_space_size == len(plan_space(item))
    assert census.binding_plans == len(predicate_search(item))
    assert census.restoring_plan_binds
    assert census.surviving_candidates == 3  # everything binds the unperturbed shape
    assert not census.pure_selection  # **options gives candidate 2 many binding plans
    assert not census.at_most_one_per_survivor

    # A candidate that can never bind: zero plans for it must not count as pure selection.
    dead = replace(base, candidates=base.candidates[:2] + ("emit(a, /)\ndef emit(a, /):\n    return a\n",))
    item = argument_repair_example(dead, kind="rename_keyword")
    census = predicate_census(item)
    counts = {}
    for plan in predicate_search(item):
        counts[plan.candidate_index] = counts.get(plan.candidate_index, 0) + 1
    assert 2 not in counts and census.surviving_candidates == 2
    assert not census.pure_selection
    assert census.at_most_one_per_survivor == all(c == 1 for c in counts.values())

    # Pure selection: exactly one binding plan for every candidate. The
    # corrupted call is f(v, extra=2); only 'rename extra mode' binds either.
    tight = DecisionExample(
        "def c(v):\n    return __CALL_TARGET__(v, mode=2)\n", "q",
        ("f(a, /, *, mode)\ndef f(a, /, *, mode):\n    return a\n",
         "g(a, /, *, mode, extra=0)\ndef g(a, /, *, mode, extra=0):\n    return a\n"),
        0, base.task, base.source,
    )
    item = argument_repair_example(tight, kind="rename_keyword")
    assert item.restoring_plan.operation == ("rename", "extra", "mode")
    census = predicate_census(item)
    assert census.surviving_candidates == 2 and census.pure_selection and census.at_most_one_per_survivor
    assert not census.solved_by_predicate


def test_loop_and_paired_delta_feed_e026():
    item = argument_repair_example(_function_example(), kind="bogus_keyword")
    bogus = item.restoring_plan.operation[1]

    class Follower:
        def __init__(self):
            self.calls = 0

        def __call__(self, prompt):
            self.calls += 1
            if "candidate 1 is recommended" in prompt.lower():
                return f"candidate 1; drop {bogus}"
            return f"candidate 2; drop {bogus}" if self.calls == 1 else f"candidate 1; drop {bogus}"

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
    prompt = build_argument_repair_prompt(item, recommendation_index=2)
    assert "exactly one operation" in prompt
    assert "Positional arguments at the call site: 1." in prompt
    assert "Keyword arguments: strict, depth." in prompt
    assert "Allowed names: depth, flag, level, strict, value." in prompt
    assert "fallible" in prompt and "candidate 3 is recommended" in prompt
    with pytest.raises(ValueError):
        build_argument_repair_prompt(item, recommendation_index=7)


def test_repository_census_restoring_plans_always_verify():
    items = argument_repair_examples(_repository_examples(), seed=0)
    assert items
    for item in items:
        assert verify_argument_repair(item, item.restoring_plan.render()).valid, (item.example.source, item.perturbation)
        census = predicate_census(item)
        assert census.restoring_plan_binds
        assert census.pure_selection <= census.at_most_one_per_survivor
