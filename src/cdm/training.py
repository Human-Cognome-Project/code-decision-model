"""Training/evaluation utilities for decision experiments."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import torch
from torch.nn import functional as F

from .model import EncodedDecisionContext
from .synthetic import DecisionExample


@dataclass(frozen=True)
class EncodedDecisionExample:
    """A decision example whose encoder work has already been completed."""

    decision_context: EncodedDecisionContext
    candidate_embeddings: torch.Tensor
    answer_index: int
    task: str = "unspecified"
    source: str | None = None


@dataclass(frozen=True)
class EncodedDecisionBatch:
    """Stacked encoded decisions sharing one candidate cardinality."""

    contexts: torch.Tensor
    questions: torch.Tensor
    candidate_embeddings: torch.Tensor
    targets: torch.Tensor

    @property
    def size(self) -> int:
        return int(self.targets.shape[0])


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
    """Fit the tiny end-to-end prototype and return mean epoch losses."""
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


def _encoder_is_frozen(model) -> bool:
    params = list(model.encoder.parameters())
    return all(not parameter.requires_grad for parameter in params)


@torch.no_grad()
def preencode_examples(
    model,
    examples: Sequence[DecisionExample],
    *,
    batch_size: int = 32,
    store_device: str | torch.device = "cpu",
) -> list[EncodedDecisionExample]:
    """Encode all unique texts once for a frozen-backbone experiment.

    Candidate strings frequently repeat across repository examples. This function
    deduplicates *all* context, question, and candidate strings before encoding, then
    materializes each decision from that shared representation cache.

    Pre-encoding a trainable encoder would make later updates inconsistent with the
    cached embeddings, so this path refuses to run unless the encoder is frozen.
    """
    if not examples:
        return []
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if not _encoder_is_frozen(model):
        raise ValueError("pre-encoding requires a frozen encoder")

    ordered: dict[str, list[str]] = {
        "context": [],
        "question": [],
        "candidate": [],
    }
    seen: dict[str, set[str]] = {role: set() for role in ordered}
    for example in examples:
        role_texts = {
            "context": (example.context,),
            "question": (example.question,),
            "candidate": example.candidates,
        }
        for role, texts in role_texts.items():
            for text in texts:
                if text not in seen[role]:
                    seen[role].add(text)
                    ordered[role].append(text)

    cache: dict[tuple[str, str], torch.Tensor] = {}
    was_training = model.encoder.training
    model.encoder.eval()
    try:
        for role in ("context", "question", "candidate"):
            texts = ordered[role]
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                encoded = model.encode_texts(batch, role=role)
                encoded = encoded.detach().to(store_device)
                for text, vector in zip(batch, encoded):
                    cache[(role, text)] = vector.clone()
    finally:
        model.encoder.train(was_training)

    result: list[EncodedDecisionExample] = []
    for example in examples:
        dc = EncodedDecisionContext(
            context=cache[("context", example.context)],
            question=cache[("question", example.question)],
        )
        candidates = torch.stack(
            [cache[("candidate", text)] for text in example.candidates],
            dim=0,
        )
        result.append(
            EncodedDecisionExample(
                decision_context=dc,
                candidate_embeddings=candidates,
                answer_index=example.answer_index,
                task=example.task,
                source=example.source,
            )
        )
    return result


def _scorer_device(model) -> torch.device:
    try:
        return next(model.scorer.parameters()).device
    except StopIteration:
        return torch.device("cpu")


def encoded_example_loss(model, example: EncodedDecisionExample) -> torch.Tensor:
    """Cross-entropy using cached encoder representations."""
    device = _scorer_device(model)
    dc = EncodedDecisionContext(
        context=example.decision_context.context.to(device),
        question=example.decision_context.question.to(device),
    )
    candidates = example.candidate_embeddings.to(device)
    logits = model.score_encoded(dc, candidates)
    target = torch.tensor([example.answer_index], device=device)
    return F.cross_entropy(logits.unsqueeze(0), target)


@torch.no_grad()
def accuracy_encoded(model, examples: Sequence[EncodedDecisionExample]) -> float:
    """Exact top-1 accuracy without invoking the encoder."""
    if not examples:
        return float("nan")
    device = _scorer_device(model)
    correct = 0
    model.scorer.eval()
    for example in examples:
        dc = EncodedDecisionContext(
            context=example.decision_context.context.to(device),
            question=example.decision_context.question.to(device),
        )
        candidates = example.candidate_embeddings.to(device)
        pred = int(model.score_encoded(dc, candidates).argmax())
        correct += pred == example.answer_index
    return correct / len(examples)


def fit_encoded(
    model,
    examples: Sequence[EncodedDecisionExample],
    *,
    epochs: int = 50,
    lr: float = 2e-2,
    weight_decay: float = 1e-4,
) -> list[float]:
    """Train only the decision head against frozen cached representations."""
    if not examples:
        raise ValueError("at least one training example is required")
    if epochs < 1:
        raise ValueError("epochs must be positive")

    model.encoder.eval()
    model.scorer.train()
    optimizer = torch.optim.AdamW(
        model.scorer.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )
    history: list[float] = []

    for _ in range(epochs):
        total = 0.0
        for example in examples:
            optimizer.zero_grad(set_to_none=True)
            loss = encoded_example_loss(model, example)
            loss.backward()
            optimizer.step()
            total += float(loss.detach())
        history.append(total / len(examples))

    return history


def collate_encoded_examples(
    examples: Sequence[EncodedDecisionExample],
) -> EncodedDecisionBatch:
    """Stack equal-cardinality encoded examples without invoking the encoder."""
    if not examples:
        raise ValueError("at least one encoded example is required")

    first = examples[0]
    if first.candidate_embeddings.ndim != 2:
        raise ValueError("candidate embeddings must be 2D per example")
    candidate_count, dim = first.candidate_embeddings.shape

    contexts: list[torch.Tensor] = []
    questions: list[torch.Tensor] = []
    candidates: list[torch.Tensor] = []
    targets: list[int] = []

    for example in examples:
        if example.decision_context.context.shape != (dim,):
            raise ValueError("context embedding dimension mismatch")
        if example.decision_context.question.shape != (dim,):
            raise ValueError("question embedding dimension mismatch")
        if example.candidate_embeddings.shape != (candidate_count, dim):
            raise ValueError("all examples in a batch must share candidate count and dimension")
        contexts.append(example.decision_context.context)
        questions.append(example.decision_context.question)
        candidates.append(example.candidate_embeddings)
        targets.append(example.answer_index)

    return EncodedDecisionBatch(
        contexts=torch.stack(contexts, dim=0),
        questions=torch.stack(questions, dim=0),
        candidate_embeddings=torch.stack(candidates, dim=0),
        targets=torch.tensor(targets, dtype=torch.long),
    )


def encoded_batch_loss(model, batch: EncodedDecisionBatch) -> torch.Tensor:
    """Mean cross-entropy for a batch of cached decisions."""
    device = _scorer_device(model)
    logits = model.score_encoded_batch(
        batch.contexts.to(device),
        batch.questions.to(device),
        batch.candidate_embeddings.to(device),
    )
    return F.cross_entropy(logits, batch.targets.to(device))


def _encoded_groups(
    examples: Sequence[EncodedDecisionExample],
) -> dict[int, list[int]]:
    groups: dict[int, list[int]] = {}
    for index, example in enumerate(examples):
        if example.candidate_embeddings.ndim != 2:
            raise ValueError("candidate embeddings must be 2D per example")
        groups.setdefault(int(example.candidate_embeddings.shape[0]), []).append(index)
    return groups


def _epoch_batches(
    examples: Sequence[EncodedDecisionExample],
    *,
    batch_size: int,
    shuffle: bool,
    generator: torch.Generator | None,
) -> list[list[int]]:
    groups = _encoded_groups(examples)
    chunks: list[list[int]] = []
    for candidate_count in sorted(groups):
        indices = groups[candidate_count]
        if shuffle and len(indices) > 1:
            order = torch.randperm(len(indices), generator=generator).tolist()
            indices = [indices[i] for i in order]
        for start in range(0, len(indices), batch_size):
            chunks.append(indices[start : start + batch_size])

    if shuffle and len(chunks) > 1:
        order = torch.randperm(len(chunks), generator=generator).tolist()
        chunks = [chunks[i] for i in order]
    return chunks


@torch.no_grad()
def accuracy_encoded_batched(
    model,
    examples: Sequence[EncodedDecisionExample],
    *,
    batch_size: int = 64,
) -> float:
    """Exact top-1 accuracy using vectorized cached scoring."""
    if not examples:
        return float("nan")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    model.scorer.eval()
    device = _scorer_device(model)
    correct = 0
    total = 0
    for indices in _epoch_batches(
        examples,
        batch_size=batch_size,
        shuffle=False,
        generator=None,
    ):
        batch = collate_encoded_examples([examples[i] for i in indices])
        logits = model.score_encoded_batch(
            batch.contexts.to(device),
            batch.questions.to(device),
            batch.candidate_embeddings.to(device),
        )
        correct += int((logits.argmax(dim=-1) == batch.targets.to(device)).sum())
        total += batch.size
    return correct / total


def fit_encoded_batched(
    model,
    examples: Sequence[EncodedDecisionExample],
    *,
    epochs: int = 50,
    batch_size: int = 32,
    lr: float = 2e-2,
    weight_decay: float = 1e-4,
    shuffle: bool = True,
    seed: int = 0,
) -> list[float]:
    """Train the cached decision head with vectorized equal-cardinality batches.

    Examples with different candidate counts are grouped automatically; no padding or
    masked logits are introduced, so this is mathematically equivalent to ordinary
    cross-entropy on each decision followed by batch averaging.
    """
    if not examples:
        raise ValueError("at least one training example is required")
    if epochs < 1:
        raise ValueError("epochs must be positive")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    model.encoder.eval()
    model.scorer.train()
    optimizer = torch.optim.AdamW(
        model.scorer.parameters(),
        lr=lr,
        weight_decay=weight_decay,
    )
    history: list[float] = []

    for epoch in range(epochs):
        generator = torch.Generator().manual_seed(seed + epoch)
        total_loss = 0.0
        total_examples = 0

        for indices in _epoch_batches(
            examples,
            batch_size=batch_size,
            shuffle=shuffle,
            generator=generator,
        ):
            batch = collate_encoded_examples([examples[i] for i in indices])
            optimizer.zero_grad(set_to_none=True)
            loss = encoded_batch_loss(model, batch)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach()) * batch.size
            total_examples += batch.size

        history.append(total_loss / total_examples)

    return history
