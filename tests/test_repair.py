import ast

from cdm.repair import (
    build_repair_prompt,
    candidate_symbol,
    expected_repair_source,
    feedback_for,
    run_paired_repair,
    run_repair_loop,
    verify_repair,
)
from cdm.synthetic import DecisionExample


def _function_example():
    return DecisionExample(
        context="""def caller(value):
    prepared = value.strip()
    return __CALL_TARGET__(prepared)
""",
        question="Which candidate definition should replace __CALL_TARGET__?",
        candidates=(
            """normalize(value)
def normalize(value):
    return value.lower()
""",
            """parse(value)
def parse(value):
    return int(value)
""",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="example.py",
    )


def _method_example():
    return DecisionExample(
        context="""def caller(self, value):
    return self.__CALL_TARGET__(value)
""",
        question="Which candidate method should replace __CALL_TARGET__?",
        candidates=(
            """decode(self, value)
def decode(self, value):
    return bytes(value)
""",
            """clean(self, value)
def clean(self, value):
    return value.strip()
""",
        ),
        answer_index=1,
        task="python.hard_masked_same_class_call",
        source="example.py",
    )


def test_candidate_symbol_reads_rendered_signature():
    rendered = (
        "clean(self, value)\n"
        "def clean(self, value):\n"
        "    pass"
    )
    assert candidate_symbol(rendered) == "clean"


def test_expected_function_repair_resolves_marker():
    source = expected_repair_source(_function_example())
    tree = ast.parse(source)

    assert "__CALL_TARGET__" not in source
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "normalize"
        for node in ast.walk(tree)
    )


def test_exact_function_repair_accepts_raw_or_fenced_code():
    example = _function_example()
    expected = expected_repair_source(example)

    assert verify_repair(example, expected).valid

    fence = chr(96) * 3
    fenced = fence + "python\n" + expected + "\n" + fence
    assert verify_repair(example, fenced).valid


def test_exact_method_repair_is_supported():
    example = _method_example()
    expected = expected_repair_source(example)

    assert verify_repair(example, expected).valid


def test_wrong_target_and_unrelated_changes_fail():
    example = _function_example()

    wrong = """def caller(value):
    prepared = value.strip()
    return parse(prepared)
"""
    changed = """def caller(value):
    prepared = value.upper()
    return normalize(prepared)
"""

    assert verify_repair(example, wrong).reason == "wrong_target"
    assert verify_repair(example, changed).reason == "unrelated_change"



def test_extra_module_statements_are_rejected():
    example = _function_example()
    expected = expected_repair_source(example)
    generated = "helper = 1" + chr(10) + expected

    assert verify_repair(example, generated).reason == "invalid_python"

def test_feedback_does_not_reveal_correct_candidate():
    example = _function_example()
    result = verify_repair(
        example,
        """def caller(value):
    prepared = value.strip()
    return parse(prepared)
""",
    )
    feedback = feedback_for(result)

    assert result.reason == "wrong_target"
    assert "normalize" not in feedback
    assert "candidate 1" not in feedback.lower()


def test_assisted_prompt_marks_recommendation_as_fallible():
    example = _function_example()
    prompt = build_repair_prompt(example, recommendation_index=1)

    assert "fallible" in prompt
    assert "candidate 2 is recommended" in prompt


def test_repair_loop_counts_a_real_corrective_turn():
    example = _function_example()
    outputs = iter([
        """def caller(value):
    prepared = value.strip()
    return parse(prepared)
""",
        expected_repair_source(example),
    ])
    prompts = []

    def generate(prompt):
        prompts.append(prompt)
        return next(outputs)

    outcome = run_repair_loop(example, generate, max_attempts=3)

    assert outcome.success
    assert outcome.attempts_used == 2
    assert outcome.correction_turns == 1
    assert not outcome.first_pass_success
    assert "Deterministic verifier feedback" in prompts[1]
    assert "normalize" not in feedback_for(outcome.attempts[0].verification)


def test_repair_loop_respects_attempt_limit():
    example = _function_example()

    outcome = run_repair_loop(
        example,
        lambda _: "not python",
        max_attempts=2,
    )

    assert not outcome.success
    assert outcome.attempts_used == 2
    assert outcome.correction_turns == 1


def test_paired_repair_can_measure_one_fewer_correction():
    example = _function_example()
    expected = expected_repair_source(example)
    wrong = """def caller(value):
    prepared = value.strip()
    return parse(prepared)
"""

    class PromptAwareGenerator:
        def __init__(self):
            self.calls = 0

        def __call__(self, prompt):
            self.calls += 1
            if "Repository decision evidence" in prompt:
                return expected
            if self.calls == 1:
                return wrong
            return expected

    paired = run_paired_repair(
        example,
        PromptAwareGenerator,
        recommendation_index=0,
        max_attempts=3,
    )

    assert paired.baseline.success
    assert paired.assisted.success
    assert paired.baseline.correction_turns == 1
    assert paired.assisted.correction_turns == 0
    assert paired.success_delta == 0
    assert paired.correction_turn_delta == 1


def test_unresolved_pair_does_not_invent_turn_delta():
    example = _function_example()
    expected = expected_repair_source(example)

    class PromptAwareGenerator:
        def __call__(self, prompt):
            if "Repository decision evidence" in prompt:
                return expected
            return "not python"

    paired = run_paired_repair(
        example,
        PromptAwareGenerator,
        recommendation_index=0,
        max_attempts=1,
    )

    assert not paired.baseline.success
    assert paired.assisted.success
    assert paired.success_delta == 1
    assert paired.correction_turn_delta is None


def test_wrong_recommendation_is_allowed_to_hurt():
    example = _function_example()
    expected = expected_repair_source(example)
    wrong = """def caller(value):
    prepared = value.strip()
    return parse(prepared)
"""

    class RecommendationFollowingGenerator:
        def __call__(self, prompt):
            if "candidate 2 is recommended" in prompt:
                return wrong
            return expected

    paired = run_paired_repair(
        example,
        RecommendationFollowingGenerator,
        recommendation_index=1,
        max_attempts=1,
    )

    assert paired.baseline.success
    assert not paired.assisted.success
    assert paired.success_delta == -1
    assert paired.correction_turn_delta is None
