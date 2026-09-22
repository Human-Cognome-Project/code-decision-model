"""Tests for unseen-repository holdout splits (E027)."""
from __future__ import annotations

import pytest

from cdm.repository import (
    RepositoryDataset,
    dataset_namespaces,
    leave_one_repository_out,
    split_repository_examples_unseen,
    verify_unseen_repository_split,
)
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


POOL = [*_make("alpha", 7), *_make("beta", 6), *_make("gamma", 5), *_make("tiny", 1)]


def test_held_out_repository_is_entirely_test_and_absent_elsewhere():
    dataset = split_repository_examples_unseen(POOL, held_out=["beta"], seed=3)

    assert _repos(dataset.test) == {"beta"}
    assert len(dataset.test) == 18
    assert "beta" not in _repos(dataset.train)
    assert "beta" not in _repos(dataset.validation)
    assert verify_unseen_repository_split(dataset) == frozenset({"beta"})


def test_retained_repositories_split_source_disjoint_with_validation():
    dataset = split_repository_examples_unseen(POOL, held_out=["gamma"], seed=1)

    assert _repos(dataset.validation) == {"alpha", "beta"}
    assert {"alpha", "beta", "tiny"} <= _repos(dataset.train)
    assert _sources(dataset.train).isdisjoint(_sources(dataset.validation))
    assert len(dataset.train) + len(dataset.validation) + len(dataset.test) == len(POOL)
    assert set(dataset.train + dataset.validation + dataset.test) == set(POOL)


def test_multiple_held_out_repositories():
    dataset = split_repository_examples_unseen(POOL, held_out=("alpha", "tiny"))

    assert _repos(dataset.test) == {"alpha", "tiny"}
    assert _repos(dataset.train) | _repos(dataset.validation) == {"beta", "gamma"}


def test_small_retained_namespace_policy():
    train_only = split_repository_examples_unseen(POOL, held_out=["alpha"])
    assert "tiny" in _repos(train_only.train)
    assert "tiny" not in _repos(train_only.validation)

    with pytest.raises(ValueError, match="tiny"):
        split_repository_examples_unseen(POOL, held_out=["alpha"], small_namespace="error")


def test_zero_validation_fraction_keeps_everything_in_train():
    dataset = split_repository_examples_unseen(POOL, held_out=["alpha"], validation_fraction=0.0)
    assert dataset.validation == ()
    assert _repos(dataset.train) == {"beta", "gamma", "tiny"}


def test_unseen_split_is_deterministic_for_seed():
    a = split_repository_examples_unseen(POOL, held_out=["alpha"], seed=11)
    b = split_repository_examples_unseen(POOL, held_out=["alpha"], seed=11)
    assert a == b


def test_unseen_split_validation():
    with pytest.raises(ValueError, match="not present"):
        split_repository_examples_unseen(POOL, held_out=["delta"])
    with pytest.raises(ValueError, match="nothing to train"):
        split_repository_examples_unseen(POOL, held_out=["alpha", "beta", "gamma", "tiny"])
    with pytest.raises(ValueError, match="at least one"):
        split_repository_examples_unseen(POOL, held_out=[])
    with pytest.raises(ValueError, match="namespaced"):
        split_repository_examples_unseen(
            [DecisionExample("c", "q", ("a",), 0, "t", "plain.py")], held_out=["x"]
        )


def test_verify_guard_catches_leakage():
    leaked = RepositoryDataset(
        train=tuple(_make("alpha", 2)),
        validation=(),
        test=tuple(_make("alpha", 1)),
    )
    with pytest.raises(ValueError, match="leak"):
        verify_unseen_repository_split(leaked)

    empty_test = RepositoryDataset(train=tuple(_make("alpha", 2)), validation=(), test=())
    with pytest.raises(ValueError, match="no test"):
        verify_unseen_repository_split(empty_test)


def test_leave_one_repository_out_covers_every_task_exactly_once():
    folds = leave_one_repository_out(POOL, seed=5)

    assert set(folds) == {"alpha", "beta", "gamma", "tiny"}
    pooled_test: list[DecisionExample] = []
    for namespace, dataset in folds.items():
        assert verify_unseen_repository_split(dataset) == frozenset({namespace})
        pooled_test.extend(dataset.test)
    assert len(pooled_test) == len(POOL)
    assert set(pooled_test) == set(POOL)


def test_leave_one_repository_out_needs_two_repositories():
    with pytest.raises(ValueError, match="at least two"):
        leave_one_repository_out(_make("alpha", 3))


def test_dataset_namespaces_requires_provenance():
    assert dataset_namespaces(POOL) == frozenset({"alpha", "beta", "gamma", "tiny"})
    with pytest.raises(ValueError):
        dataset_namespaces([DecisionExample("c", "q", ("a",), 0, "t", None)])
