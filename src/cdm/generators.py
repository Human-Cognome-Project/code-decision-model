"""Generator protocol for corrective-turn experiments.

A generator is any callable that maps a repair prompt to a candidate repair
string. Real open models, mocks, and scripted oracles all satisfy the same
contract so the E021 harness stays independent of model choice.
"""
from __future__ import annotations

from typing import Callable, Protocol


class RepairGenerator(Protocol):
    """Produce a complete Python function given a repair prompt."""

    def __call__(self, prompt: str) -> str:
        ...


GeneratorFactory = Callable[[], RepairGenerator]
"""Fresh generator instance per paired arm (baseline vs assisted)."""
