"""Tests for E033 call-expression intent."""
from __future__ import annotations

from pathlib import Path

import pytest

from cdm.call_intent import (
    apply_call_intent,
    candidate_indices_for,
    build_call_intent_prompt,
    eligible,
    feedback_for_call_intent,
    masked_call_count,
    masked_call_source,
    parse_call_intent,
    run_call_intent_loop,
    run_paired_call_intent,
    verify_call_intent,
)
from cdm.corrective import summarize_paired
from cdm.repository import repository_hard_masked_call_examples
from cdm.synthetic import DecisionExample


def _function_example() -> DecisionExample:
    return DecisionExample(
        context="def caller(value):\n    prepared = value.strip()\n    return __CALL_TARGET__(prepared, strict=True)\n",
        question="q",
        candidates=(
            "normalize(value, strict)\ndef normalize(value, strict=False):\n    return value.lower()\n",
            "parse(value, strict)\ndef parse(value, strict=False):\n    return int(value)\n",
            "emit(value, mode)\ndef emit(value, mode=0):\n    return str(value)\n",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="repo::example.py",
    )


def _method_example() -> DecisionExample:
    return DecisionExample(
        context="def caller(self, value):\n    return self.__CALL_TARGET__(value)\n",
        question="q",
        candidates=(
            "decode(self, value)\ndef decode(self, value):\n    return bytes(value)\n",
            "clean(self, value)\ndef clean(self, value):\n    return value.strip()\n",
        ),
        answer_index=1,
        task="python.hard_masked_same_class_call",
        source="repo::example.py",
    )


def test_parse_accepts_fenced_backticked_and_plain_calls():
    assert parse_call_intent("normalize(prepared)") is not None
    assert parse_call_intent("```python\nnormalize(prepared)\n```") is not None
    assert parse_call_intent("`normalize(prepared)`") is not None
    assert parse_call_intent("self.clean(value);") is not None
    assert parse_call_intent("normalize") is None
    assert parse_call_intent("x = normalize(prepared)") is None
    assert parse_call_intent("def f(): pass") is None
    assert parse_call_intent("a.b.c(x)") is None  # only Name or Name.attr callees
    assert parse_call_intent("(normalize)(x)") is not None  # AST drops the parentheses


def test_apply_splices_only_the_masked_call():
    example = _function_example()
    repaired = apply_call_intent(example, parse_call_intent("normalize(prepared, strict=True)"))
    assert "__CALL_TARGET__" not in repaired
    assert "normalize(prepared, strict=True)" in repaired
    assert "value.strip()" in repaired


def test_verification_categories_are_deterministic_and_ordered():
    example = _function_example()
    cases = {
        "def f(): pass": "invalid_call_expression",
        "unknown(prepared, strict=True)": "unknown_target",
        "emit(prepared, strict=True)": "unbindable_call",  # emit has no strict=
        "parse(prepared, strict=True)": "wrong_target",
        "normalize(prepared)": "wrong_arguments",
        "normalize(value, strict=True)": "wrong_arguments",
        "normalize(prepared, strict=True)": "ok",
        "```python\nnormalize(prepared, strict=True)\n```": "ok",
    }
    for output, reason in cases.items():
        result = verify_call_intent(example, output)
        assert result.reason == reason, (output, result)
        assert result.valid == (reason == "ok")


def test_predicate_runs_before_truth_comparison():
    example = _function_example()
    # Right callee, arguments that cannot bind: predicate fires, not wrong_arguments.
    result = verify_call_intent(example, "normalize(prepared, nope=1)")
    assert result.reason == "unbindable_call"
    assert result.target_index == 0


def test_method_form_is_supported():
    example = _method_example()
    assert verify_call_intent(example, "self.clean(value)").valid
    assert verify_call_intent(example, "self.decode(value)").reason == "wrong_target"
    assert verify_call_intent(example, "clean(value)").reason == "unbindable_call"  # no receiver
    assert verify_call_intent(example, "self.clean(value=value)").reason == "wrong_arguments"
    # Receiver calls accept the bound or static reading (E024), so use a call
    # that binds under neither.
    assert verify_call_intent(example, "self.clean(value, 1, 2)").reason == "unbindable_call"
    assert verify_call_intent(example, "self.clean(value, bogus=1)").reason == "unbindable_call"


def test_feedback_never_reveals_target():
    example = _function_example()
    for output in ["parse(prepared, strict=True)", "normalize(prepared)", "emit(prepared, strict=True)", "zzz"]:
        text = feedback_for_call_intent(verify_call_intent(example, output))
        assert "normalize" not in text
        assert "candidate 1" not in text.lower()


def test_multiple_masked_call_sites_are_ineligible():
    example = _function_example()
    twice = DecisionExample(
        context="def caller(v):\n    a = __CALL_TARGET__(v, strict=True)\n    return __CALL_TARGET__(a, strict=True)\n",
        question="q", candidates=example.candidates, answer_index=0,
        task=example.task, source=example.source,
    )
    assert masked_call_count(twice) == 2
    assert not eligible(twice)
    assert verify_call_intent(twice, "normalize(v, strict=True)").reason == "unsupported_task"
    with pytest.raises(ValueError):
        build_call_intent_prompt(twice)
    assert masked_call_source(example) == "__CALL_TARGET__(prepared, strict=True)"


def test_prompt_marks_recommendation_as_fallible_and_asks_for_call_only():
    example = _function_example()
    prompt = build_call_intent_prompt(example, recommendation_index=1)
    assert "fallible" in prompt
    assert "candidate 2 is recommended" in prompt
    assert "Do not write a function" in prompt
    with pytest.raises(ValueError):
        build_call_intent_prompt(example, recommendation_index=9)


def test_loop_counts_corrections_and_paired_delta_feeds_e026():
    example = _function_example()

    class Follower:
        """Follows the recommendation with the original arguments; guesses otherwise."""

        def __init__(self):
            self.calls = 0

        def __call__(self, prompt):
            self.calls += 1
            args = masked_call_source(example).split("(", 1)[1]
            if "candidate 1 is recommended" in prompt.lower():
                return "normalize(" + args
            if self.calls == 1:
                return "parse(" + args
            return "normalize(" + args

    paired = run_paired_call_intent(example, Follower, recommendation_index=0, max_attempts=3)
    assert paired.baseline.success and paired.baseline.correction_turns == 1
    assert paired.assisted.success and paired.assisted.first_pass_success
    assert paired.correction_turn_delta == 1
    assert paired.baseline.attempts[0].verification.reason == "wrong_target"
    assert "Deterministic verifier feedback" in paired.baseline.attempts[1].prompt

    summary = summarize_paired([paired])
    assert summary.both_succeed == 1
    assert summary.correction_turn_deltas == (1,)


def test_loop_respects_budget_and_wrong_recommendation_can_hurt():
    example = _function_example()
    outcome = run_call_intent_loop(example, lambda _: "nonsense", max_attempts=2)
    assert not outcome.success and outcome.attempts_used == 2

    def follower_factory():
        return lambda prompt: (
            "parse(prepared, strict=True)" if "candidate 2 is recommended" in prompt.lower()
            else "normalize(prepared, strict=True)"
        )

    paired = run_paired_call_intent(example, follower_factory, recommendation_index=1, max_attempts=1)
    assert paired.baseline.success and not paired.assisted.success
    assert paired.success_delta == -1


def test_eligibility_census_on_this_repository():
    root = Path(__file__).resolve().parents[1]
    examples = repository_hard_masked_call_examples(root, candidate_count=4)
    assert examples
    counts = [masked_call_count(e) for e in examples]
    assert all(c >= 1 for c in counts)
    # The expected repair is always a valid intent for eligible examples.
    for example in examples:
        if not eligible(example):
            continue
        source = masked_call_source(example)
        from cdm.repair import candidate_symbol
        target = candidate_symbol(example.candidates[example.answer_index])
        intent = source.replace("__CALL_TARGET__", target)
        assert verify_call_intent(example, intent).valid, (example.source, intent)


def _duplicate_pool_example(answer_index: int) -> DecisionExample:
    """Cross-file-shaped pool: two candidates share the symbol `load`."""
    return DecisionExample(
        context="def run(v):\n    handle = open(v)\n    return __CALL_TARGET__(handle)\n",
        question="q",
        candidates=(
            "load(x)\ndef load(x):\n    return x.read()\n",
            "parse(x)\ndef parse(x):\n    return int(x)\n",
            "load(x)\ndef load(x):\n    return x.readlines()\n",
            "emit(x)\ndef emit(x):\n    return str(x)\n",
        ),
        answer_index=answer_index,
        task="python.hard_masked_cross_file_call",
        source="repo::pkg/user.py",
    )


def test_duplicate_callee_names_are_ambiguous_and_label_independent():
    first = _duplicate_pool_example(answer_index=0)
    third = _duplicate_pool_example(answer_index=2)

    assert candidate_indices_for(first, "load") == (0, 2)
    assert candidate_indices_for(first, "parse") == (1,)
    assert candidate_indices_for(first, "nope") == ()

    for example in (first, third):
        result = verify_call_intent(example, "load(handle)")
        assert not result.valid
        assert result.reason == "ambiguous_target"
        assert result.target_index is None
    # Swapping which duplicate is the answer changes nothing about the verdict.
    assert verify_call_intent(first, "load(handle)") == verify_call_intent(third, "load(handle)")

    # A unique negative still resolves and is judged on its merits.
    assert verify_call_intent(first, "parse(handle)").reason == "wrong_target"
    assert verify_call_intent(first, "nope(handle)").reason == "unknown_target"

    feedback = feedback_for_call_intent(verify_call_intent(first, "load(handle)"))
    assert "candidate 1" not in feedback.lower() and "candidate 3" not in feedback.lower()
    assert "readlines" not in feedback and "read()" not in feedback


def test_duplicate_negative_does_not_block_a_unique_answer():
    example = DecisionExample(
        context="def run(v):\n    return __CALL_TARGET__(v)\n",
        question="q",
        candidates=(
            "parse(x)\ndef parse(x):\n    return int(x)\n",
            "load(x)\ndef load(x):\n    return x.read()\n",
            "load(x)\ndef load(x):\n    return x.readlines()\n",
        ),
        answer_index=0,
        task="python.hard_masked_cross_file_call",
        source="repo::pkg/user.py",
    )
    assert verify_call_intent(example, "parse(v)").valid
    assert verify_call_intent(example, "load(v)").reason == "ambiguous_target"
