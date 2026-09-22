from cdm.evaluation import (
    accuracy,
    cluster_bootstrap_accuracy,
    cluster_bootstrap_macro_namespace_accuracy,
    macro_namespace_accuracy,
    per_namespace_accuracy,
)
from cdm.synthetic import DecisionExample


def _example(source, answer):
    return DecisionExample(
        context="x",
        question="q",
        candidates=("a", "b"),
        answer_index=answer,
        task="test",
        source=source,
    )


def test_namespace_accuracy_and_macro_weight_repositories_equally():
    examples = [
        _example("big::a.py", 0),
        _example("big::a.py", 0),
        _example("big::b.py", 0),
        _example("small::x.py", 1),
    ]
    predictions = [0, 0, 0, 0]

    assert accuracy(examples, predictions) == 0.75
    assert per_namespace_accuracy(examples, predictions) == {
        "big": 1.0,
        "small": 0.0,
    }
    assert macro_namespace_accuracy(examples, predictions) == 0.5


def test_cluster_bootstrap_is_deterministic_and_bounded():
    examples = [
        _example("repo::a.py", 0),
        _example("repo::a.py", 1),
        _example("repo::b.py", 0),
        _example("repo::c.py", 1),
        _example("repo::c.py", 0),
    ]
    predictions = [0, 0, 1, 1, 0]

    a = cluster_bootstrap_accuracy(
        examples,
        predictions,
        bootstrap_samples=500,
        seed=17,
    )
    b = cluster_bootstrap_accuracy(
        examples,
        predictions,
        bootstrap_samples=500,
        seed=17,
    )

    assert a == b
    assert a.accuracy == 0.6
    assert 0.0 <= a.lower <= a.accuracy <= a.upper <= 1.0


def test_perfect_predictions_have_degenerate_interval():
    examples = [
        _example("a::x.py", 0),
        _example("a::y.py", 1),
        _example("b::z.py", 0),
    ]
    predictions = [0, 1, 0]

    micro = cluster_bootstrap_accuracy(
        examples,
        predictions,
        bootstrap_samples=100,
    )
    macro = cluster_bootstrap_macro_namespace_accuracy(
        examples,
        predictions,
        bootstrap_samples=100,
    )

    assert (micro.accuracy, micro.lower, micro.upper) == (1.0, 1.0, 1.0)
    assert (macro.accuracy, macro.lower, macro.upper) == (1.0, 1.0, 1.0)


def test_macro_bootstrap_resamples_sources_inside_each_namespace():
    examples = [
        _example("a::x.py", 0),
        _example("a::y.py", 1),
        _example("b::x.py", 0),
        _example("b::y.py", 1),
    ]
    predictions = [0, 0, 0, 0]

    result = cluster_bootstrap_macro_namespace_accuracy(
        examples,
        predictions,
        bootstrap_samples=500,
        seed=9,
    )

    assert result.accuracy == 0.5
    assert result.lower <= 0.5 <= result.upper


def test_evaluation_validates_lengths_and_namespaces():
    examples = [_example("plain.py", 0)]

    try:
        per_namespace_accuracy(examples, [0])
    except ValueError as exc:
        assert "namespaced" in str(exc)
    else:
        raise AssertionError("expected namespace validation")

    try:
        accuracy(examples, [])
    except ValueError as exc:
        assert "equal length" in str(exc)
    else:
        raise AssertionError("expected length validation")
