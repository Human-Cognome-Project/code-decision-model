from cdm.repository import (
    namespace_repository_examples,
    split_repository_examples_balanced,
)
from cdm.synthetic import DecisionExample


def _examples(group_sizes):
    result = []
    for source, size in group_sizes.items():
        for i in range(size):
            result.append(
                DecisionExample(
                    context=f"context {source} {i}",
                    question="choose",
                    candidates=("a", "b"),
                    answer_index=i % 2,
                    task="test",
                    source=source,
                )
            )
    return result


def _sources(examples):
    return {example.source for example in examples}


def test_balanced_split_is_source_disjoint_and_nonempty():
    examples = _examples({
        "a.py": 20,
        "b.py": 15,
        "c.py": 12,
        "d.py": 10,
        "e.py": 8,
        "f.py": 7,
        "g.py": 6,
        "h.py": 5,
        "i.py": 4,
        "j.py": 3,
        "k.py": 2,
        "l.py": 1,
    })
    dataset = split_repository_examples_balanced(
        examples,
        seed=9,
        train_fraction=0.7,
        validation_fraction=0.15,
    )

    assert dataset.train
    assert dataset.validation
    assert dataset.test

    train_sources = _sources(dataset.train)
    val_sources = _sources(dataset.validation)
    test_sources = _sources(dataset.test)

    assert train_sources.isdisjoint(val_sources)
    assert train_sources.isdisjoint(test_sources)
    assert val_sources.isdisjoint(test_sources)
    assert train_sources | val_sources | test_sources == set(
        e.source for e in examples
    )

    total = len(examples)
    max_group = 20
    assert abs(len(dataset.train) - total * 0.7) <= max_group
    assert abs(len(dataset.validation) - total * 0.15) <= max_group
    assert abs(len(dataset.test) - total * 0.15) <= max_group


def test_balanced_split_is_deterministic_for_seed():
    examples = _examples({f"f{i}.py": 3 for i in range(12)})

    a = split_repository_examples_balanced(examples, seed=17)
    b = split_repository_examples_balanced(examples, seed=17)

    assert a == b


def test_balanced_split_seed_changes_equal_sized_group_assignment():
    examples = _examples({f"f{i}.py": 2 for i in range(18)})

    a = split_repository_examples_balanced(examples, seed=1)
    b = split_repository_examples_balanced(examples, seed=2)

    assert (
        _sources(a.train),
        _sources(a.validation),
        _sources(a.test),
    ) != (
        _sources(b.train),
        _sources(b.validation),
        _sources(b.test),
    )


def test_balanced_split_rejects_too_few_source_groups():
    examples = _examples({"a.py": 4, "b.py": 4})

    try:
        split_repository_examples_balanced(examples)
    except ValueError as exc:
        assert "source groups" in str(exc)
    else:
        raise AssertionError("expected source-group validation")


def test_balanced_split_supports_no_validation_partition():
    examples = _examples({f"f{i}.py": 2 for i in range(6)})
    dataset = split_repository_examples_balanced(
        examples,
        validation_fraction=0.0,
    )

    assert dataset.train
    assert not dataset.validation
    assert dataset.test
    assert _sources(dataset.train).isdisjoint(_sources(dataset.test))


def test_namespace_repository_examples_prevents_path_collisions():
    source = _examples({"src/main.py": 2})

    a = namespace_repository_examples(source, "repo-a")
    b = namespace_repository_examples(source, "repo-b")

    assert _sources(a) == {"repo-a::src/main.py"}
    assert _sources(b) == {"repo-b::src/main.py"}
    assert a[0].context == source[0].context
    assert a[0].candidates == source[0].candidates


def test_namespace_requires_repository_provenance():
    example = DecisionExample(
        context="x",
        question="q",
        candidates=("a", "b"),
        answer_index=0,
    )

    try:
        namespace_repository_examples([example], "repo")
    except ValueError as exc:
        assert "provenance" in str(exc)
    else:
        raise AssertionError("expected provenance validation")
