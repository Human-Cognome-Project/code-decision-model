from cdm.repository import split_repository_examples_by_namespace
from cdm.synthetic import DecisionExample


def _make(namespace, files, per_file=3):
    result = []
    for file_index in range(files):
        source = f"{namespace}::pkg/f{file_index}.py"
        for i in range(per_file):
            result.append(
                DecisionExample(
                    context=f"{namespace} {file_index} {i}",
                    question="q",
                    candidates=("a", "b"),
                    answer_index=i % 2,
                    task="test",
                    source=source,
                )
            )
    return result


def _repos(examples):
    return {e.source.split("::", 1)[0] for e in examples}


def _sources(examples):
    return {e.source for e in examples}


def test_namespace_stratification_represents_evaluable_repos_in_all_splits():
    examples = [
        *_make("alpha", 7),
        *_make("beta", 6),
        *_make("tiny", 2),
    ]

    dataset = split_repository_examples_by_namespace(
        examples,
        seed=3,
        train_fraction=0.7,
        validation_fraction=0.15,
        small_namespace="train",
    )

    assert {"alpha", "beta"}.issubset(_repos(dataset.train))
    assert _repos(dataset.validation) == {"alpha", "beta"}
    assert _repos(dataset.test) == {"alpha", "beta"}

    assert "tiny" in _repos(dataset.train)
    assert "tiny" not in _repos(dataset.validation)
    assert "tiny" not in _repos(dataset.test)

    assert _sources(dataset.train).isdisjoint(_sources(dataset.validation))
    assert _sources(dataset.train).isdisjoint(_sources(dataset.test))
    assert _sources(dataset.validation).isdisjoint(_sources(dataset.test))


def test_namespace_stratification_is_deterministic():
    examples = [*_make("alpha", 8), *_make("beta", 8)]

    a = split_repository_examples_by_namespace(examples, seed=11)
    b = split_repository_examples_by_namespace(examples, seed=11)

    assert a == b


def test_namespace_stratification_can_reject_small_repositories():
    examples = [*_make("alpha", 5), *_make("tiny", 2)]

    try:
        split_repository_examples_by_namespace(
            examples,
            small_namespace="error",
        )
    except ValueError as exc:
        assert "tiny" in str(exc)
        assert "source groups" in str(exc)
    else:
        raise AssertionError("expected small namespace rejection")


def test_namespace_stratification_requires_namespaced_sources():
    example = DecisionExample(
        context="x",
        question="q",
        candidates=("a", "b"),
        answer_index=0,
        task="test",
        source="plain.py",
    )

    try:
        split_repository_examples_by_namespace([example])
    except ValueError as exc:
        assert "namespaced" in str(exc)
    else:
        raise AssertionError("expected namespace provenance validation")


def test_namespace_stratification_supports_two_way_split():
    examples = [*_make("alpha", 4), *_make("beta", 4)]
    dataset = split_repository_examples_by_namespace(
        examples,
        validation_fraction=0.0,
    )

    assert dataset.train
    assert not dataset.validation
    assert dataset.test
    assert _repos(dataset.test) == {"alpha", "beta"}
