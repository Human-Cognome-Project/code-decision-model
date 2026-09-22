from cdm.synthetic import python_definition_examples


def test_python_definition_examples_are_machine_labeled():
    src = """
def alpha(x):
    return x + 1

def beta(y):
    return y * 2

def gamma(z):
    return z - 3
"""
    examples = python_definition_examples(src)
    assert len(examples) == 3
    assert [e.candidates[e.answer_index].split("(")[0] for e in examples] == [
        "alpha", "beta", "gamma"
    ]
