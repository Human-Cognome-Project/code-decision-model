import torch

from cdm import CodeDecisionModel, HashTextEncoder
from cdm.synthetic import python_direct_call_examples
from cdm.training import accuracy, fit


SOURCE = """
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


def test_tiny_model_can_learn_machine_verified_call_decisions():
    torch.manual_seed(7)
    examples = python_direct_call_examples(SOURCE)
    model = CodeDecisionModel(
        encoder=HashTextEncoder(dim=32, buckets=2048),
        dim=32,
        hidden=48,
    )

    history = fit(model, examples, epochs=80)

    assert history[-1] < history[0] * 0.05
    assert accuracy(model, examples) == 1.0
