import ast

from cdm.ablation import ablate_hard_call_identifiers
from cdm.synthetic import DecisionExample


def _example():
    return DecisionExample(
        context="""def caller(value):
    return __CALL_TARGET__(value) + caller_helper(value)
""",
        question="Which candidate definition should replace __CALL_TARGET__ in this caller?",
        candidates=(
            """target(value)
def target(value):
    if value <= 0:
        return 0
    return target(value - 1) + value""",
            """alternate(value)
def alternate(value):
    return value * 2""",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="repo::module.py",
    )


def test_identifier_ablation_masks_caller_and_candidate_own_names():
    example = _example()
    masked = ablate_hard_call_identifiers(example)

    assert "def __CALLER__" in masked.context
    assert "def caller(" not in masked.context
    assert "__CALL_TARGET__" in masked.context

    assert all("def __CANDIDATE__" in c for c in masked.candidates)
    assert "target" not in masked.candidates[0]
    assert "alternate" not in masked.candidates[1]

    tree = ast.parse(masked.candidates[0])
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "__CANDIDATE__" in names

    assert masked.answer_index == example.answer_index
    assert masked.source == example.source


def test_caller_only_ablation_preserves_candidates():
    example = _example()
    masked = ablate_hard_call_identifiers(
        example,
        caller=True,
        candidates=False,
    )

    assert "__CALLER__" in masked.context
    assert masked.candidates == example.candidates


def test_candidate_only_ablation_preserves_caller():
    example = _example()
    masked = ablate_hard_call_identifiers(
        example,
        caller=False,
        candidates=True,
    )

    assert masked.context == example.context
    assert all("__CANDIDATE__" in c for c in masked.candidates)


def test_ablation_rejects_wrong_task():
    example = _example()
    wrong = DecisionExample(
        context=example.context,
        question=example.question,
        candidates=example.candidates,
        answer_index=0,
        task="other",
        source=example.source,
    )

    try:
        ablate_hard_call_identifiers(wrong)
    except ValueError as exc:
        assert "hard masked-call" in str(exc)
    else:
        raise AssertionError("expected task validation")
