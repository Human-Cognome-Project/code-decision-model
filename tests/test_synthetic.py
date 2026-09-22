from cdm.synthetic import python_definition_examples, python_direct_call_examples


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


def test_python_definition_examples_are_machine_labeled():
    examples = python_definition_examples(SOURCE)
    assert len(examples) == 6
    assert [e.candidates[e.answer_index].split("(")[0] for e in examples] == [
        "normalize", "parse", "clamp", "stage_one", "stage_two", "stage_three"
    ]


def test_python_direct_call_examples_follow_ast_edges():
    examples = python_direct_call_examples(SOURCE)
    assert len(examples) == 3
    targets = [e.candidates[e.answer_index].split("(")[0] for e in examples]
    assert targets == ["normalize", "parse", "clamp"]
