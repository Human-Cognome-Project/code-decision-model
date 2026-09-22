"""Minimal training/evaluation utilities for decision experiments."""
from __future__ import annotations

from collections.abc import Sequence

import torch
from torch.nn import functional as F

from .synthetic import DecisionExample


def example_loss(model, example: DecisionExample) -> torch.Tensor:
    """Cross-entropy over a runtime-defined candidate set."""
    logits = model(example.context, example.question, example.candidates)
    target = torch.tensor([example.answer_index], device=logits.device)
    return F.cross_entropy(logits.unsqueeze(0), target)


@torch.no_grad()
def accuracy(model, examples: Sequence[DecisionExample]) -> float:
    """Exact top-1 candidate accuracy."""
    if not examples:
        return float("nan")
    correct = 0
    for example in examples:
        pred = int(model(
            example.context,
            example.question,
            example.candidates,
        ).argmax())
        correct += pred == example.answer_index
    return correct / len(examples)


def fit(
    model,
    examples: Sequence[DecisionExample],
    *,
    epochs: int = 50,
    lr: float = 2e-2,
    weight_decay: float = 1e-4,
) -> list[float]:
    """Fit the tiny prototype and return mean epoch losses.

    This deliberately simple loop is for architectural experiments, not large-scale
    training. A real pretrained encoder will need batching, mixed precision,
    checkpointing, held-out calibration, and proper experiment tracking.
    """
    if not examples:
        raise ValueError("at least one training example is required")
    if epochs < 1:
        raise ValueError("epochs must be positive")

    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )
    history: list[float] = []

    for _ in range(epochs):
        total = 0.0
        for example in examples:
            optimizer.zero_grad(set_to_none=True)
            loss = example_loss(model, example)
            loss.backward()
            optimizer.step()
            total += float(loss.detach())
        history.append(total / len(examples))

    return history
