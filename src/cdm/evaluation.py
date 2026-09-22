"""Evaluation helpers that respect repository/source grouping."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from .synthetic import DecisionExample


@dataclass(frozen=True)
class AccuracyInterval:
    """Point estimate and percentile bootstrap interval."""

    accuracy: float
    lower: float
    upper: float
    samples: int
    confidence: float


def _validate(
    examples: Sequence[DecisionExample],
    predictions: Sequence[int],
) -> None:
    if not examples:
        raise ValueError("at least one example is required")
    if len(examples) != len(predictions):
        raise ValueError("examples and predictions must have equal length")
    if any(example.source is None for example in examples):
        raise ValueError("evaluation requires source provenance")


def accuracy(
    examples: Sequence[DecisionExample],
    predictions: Sequence[int],
) -> float:
    """Exact top-1 accuracy."""
    _validate(examples, predictions)
    return sum(
        int(prediction == example.answer_index)
        for example, prediction in zip(examples, predictions)
    ) / len(examples)


def per_namespace_accuracy(
    examples: Sequence[DecisionExample],
    predictions: Sequence[int],
) -> dict[str, float]:
    """Accuracy by repository namespace in sources of the form namespace::path."""
    _validate(examples, predictions)
    counts: dict[str, list[int]] = {}
    for example, prediction in zip(examples, predictions):
        if "::" not in example.source:
            raise ValueError("namespace accuracy requires namespaced source provenance")
        namespace, _ = example.source.split("::", 1)
        bucket = counts.setdefault(namespace, [0, 0])
        bucket[0] += int(prediction == example.answer_index)
        bucket[1] += 1
    return {
        namespace: correct / total
        for namespace, (correct, total) in sorted(counts.items())
    }


def macro_namespace_accuracy(
    examples: Sequence[DecisionExample],
    predictions: Sequence[int],
) -> float:
    """Give each repository namespace equal weight regardless of example count."""
    values = per_namespace_accuracy(examples, predictions)
    return sum(values.values()) / len(values)


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires values")
    if q <= 0.0:
        return sorted_values[0]
    if q >= 1.0:
        return sorted_values[-1]
    position = q * (len(sorted_values) - 1)
    lo = int(position)
    hi = min(lo + 1, len(sorted_values) - 1)
    weight = position - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def _interval(
    point: float,
    bootstrap: list[float],
    *,
    confidence: float,
) -> AccuracyInterval:
    bootstrap.sort()
    alpha = (1.0 - confidence) / 2.0
    return AccuracyInterval(
        accuracy=point,
        lower=_percentile(bootstrap, alpha),
        upper=_percentile(bootstrap, 1.0 - alpha),
        samples=len(bootstrap),
        confidence=confidence,
    )


def cluster_bootstrap_accuracy(
    examples: Sequence[DecisionExample],
    predictions: Sequence[int],
    *,
    bootstrap_samples: int = 5000,
    confidence: float = 0.95,
    seed: int = 0,
) -> AccuracyInterval:
    """Bootstrap source files, not individual examples.

    Examples from one source file are correlated because they share naming/style and
    candidate pools. Resampling examples independently would therefore understate
    uncertainty.
    """
    _validate(examples, predictions)
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    groups: dict[str, tuple[int, int]] = {}
    mutable: dict[str, list[int]] = {}
    for example, prediction in zip(examples, predictions):
        bucket = mutable.setdefault(example.source, [0, 0])
        bucket[0] += int(prediction == example.answer_index)
        bucket[1] += 1
    groups = {source: (v[0], v[1]) for source, v in mutable.items()}
    keys = sorted(groups)

    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(bootstrap_samples):
        correct = 0
        total = 0
        for _ in range(len(keys)):
            key = keys[rng.randrange(len(keys))]
            c, n = groups[key]
            correct += c
            total += n
        values.append(correct / total)

    return _interval(
        accuracy(examples, predictions),
        values,
        confidence=confidence,
    )


def cluster_bootstrap_macro_namespace_accuracy(
    examples: Sequence[DecisionExample],
    predictions: Sequence[int],
    *,
    bootstrap_samples: int = 5000,
    confidence: float = 0.95,
    seed: int = 0,
) -> AccuracyInterval:
    """Bootstrap source files within each repository, then macro-average repositories."""
    _validate(examples, predictions)
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between 0 and 1")

    groups: dict[str, dict[str, list[int]]] = {}
    for example, prediction in zip(examples, predictions):
        if "::" not in example.source:
            raise ValueError("macro bootstrap requires namespaced source provenance")
        namespace, _ = example.source.split("::", 1)
        bucket = groups.setdefault(namespace, {}).setdefault(example.source, [0, 0])
        bucket[0] += int(prediction == example.answer_index)
        bucket[1] += 1

    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(bootstrap_samples):
        namespace_scores = []
        for namespace in sorted(groups):
            source_groups = groups[namespace]
            keys = sorted(source_groups)
            correct = 0
            total = 0
            for _ in range(len(keys)):
                key = keys[rng.randrange(len(keys))]
                c, n = source_groups[key]
                correct += c
                total += n
            namespace_scores.append(correct / total)
        values.append(sum(namespace_scores) / len(namespace_scores))

    return _interval(
        macro_namespace_accuracy(examples, predictions),
        values,
        confidence=confidence,
    )
