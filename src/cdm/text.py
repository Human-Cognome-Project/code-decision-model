"""Small dependency-free text/code encoder used for architecture experiments.

This is deliberately not the intended production encoder. It gives the prototype a
trainable CPU baseline without requiring model downloads.
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

import torch
from torch import nn

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]")


class HashTextEncoder(nn.Module):
    """Hash tokens into a trainable embedding table and mean-pool them.

    Hashing keeps the experimental model vocabulary-free while preserving a stable
    mapping across runs. A code-native pretrained encoder can replace this class
    without changing the decision model interface.
    """

    def __init__(self, dim: int = 128, buckets: int = 32768) -> None:
        super().__init__()
        if dim < 1 or buckets < 2:
            raise ValueError("dim and buckets must be positive")
        self.dim = dim
        self.buckets = buckets
        self.embedding = nn.Embedding(buckets, dim)

    def _id(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "little") % self.buckets

    def token_ids(self, text: str) -> list[int]:
        ids = [self._id(t) for t in _TOKEN.findall(text)]
        return ids or [self._id("<empty>")]

    def encode_many(self, texts: Iterable[str], device: torch.device | None = None) -> torch.Tensor:
        seqs = [self.token_ids(text) for text in texts]
        if not seqs:
            return torch.empty((0, self.dim), device=device or self.embedding.weight.device)
        target = device or self.embedding.weight.device
        pooled = []
        for ids in seqs:
            t = torch.tensor(ids, dtype=torch.long, device=target)
            pooled.append(self.embedding(t).mean(dim=0))
        return torch.stack(pooled, dim=0)

    def forward(self, texts: Iterable[str]) -> torch.Tensor:
        return self.encode_many(texts)
