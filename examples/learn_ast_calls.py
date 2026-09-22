"""Run the first falsifiable learning experiment.

Usage:
    python examples/learn_ast_calls.py
"""
import torch

from cdm import CodeDecisionModel, HashTextEncoder
from cdm.synthetic import python_direct_call_examples
from cdm.training import accuracy, fit


TRAIN_SOURCE = """
def normalize(x):
    return x.strip()

def parse(x):
    return int(x)

def clamp(x):
    return max(0, x)

def stage_one(x):
    return normalize(x)

def stage_two(x):
    return parse(x)

def stage_three(x):
    return clamp(x)
"""

HELD_OUT_SOURCE = """
def normalize(x):
    return x.strip()

def parse(x):
    return int(x)

def clamp(x):
    return max(0, x)

def clean_value(x):
    return normalize(x)

def read_value(x):
    return parse(x)

def bound_value(x):
    return clamp(x)
"""


def main() -> None:
    torch.manual_seed(7)
    train = python_direct_call_examples(TRAIN_SOURCE)
    held_out = python_direct_call_examples(HELD_OUT_SOURCE)

    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=32, buckets=2048),
        dim=32,
        hidden=48,
    )

    before_train = accuracy(model, train)
    before_held_out = accuracy(model, held_out)
    history = fit(model, train, epochs=100)
    after_train = accuracy(model, train)
    after_held_out = accuracy(model, held_out)

    print(f"examples: train={len(train)} held_out={len(held_out)}")
    print(f"loss: {history[0]:.4f} -> {history[-1]:.6f}")
    print(f"train accuracy: {before_train:.3f} -> {after_train:.3f}")
    print(f"held-out accuracy: {before_held_out:.3f} -> {after_held_out:.3f}")
    print()
    print("Interpretation: fitting proves only that the decision path can learn.")
    print("Held-out behavior of the toy hash encoder is diagnostic, not a capability claim.")


if __name__ == "__main__":
    main()
