from cdm.repository import (
    repository_call_examples,
    repository_hard_masked_call_examples,
)


def _write(tmp_path, source):
    path = tmp_path / "module.py"
    path.write_text(source, encoding="utf-8")
    return path


def _candidate_names(example):
    return {
        candidate.split("\n", 1)[0].split("(", 1)[0]
        for candidate in example.candidates
    }


def test_nested_function_calls_are_not_attributed_to_outer_function(tmp_path):
    _write(
        tmp_path,
        """
def nested_target(x):
    return x + 1

def direct_target(x):
    return x * 2

def outer(x):
    def inner():
        return nested_target(x)
    return direct_target(x)
""",
    )

    examples = repository_call_examples(tmp_path, max_candidates=3, seed=0)

    assert len(examples) == 1
    example = examples[0]
    assert "outer" in example.question
    assert example.candidates[example.answer_index].split("::", 1)[1].startswith(
        "direct_target("
    )


def test_nested_only_call_does_not_create_false_outer_edge(tmp_path):
    _write(
        tmp_path,
        """
def target(x):
    return x + 1

def outer(x):
    def inner():
        return target(x)
    return inner
""",
    )

    assert repository_call_examples(tmp_path, max_candidates=2, seed=0) == []


def test_textual_target_name_leak_causes_masked_example_rejection(tmp_path):
    _write(
        tmp_path,
        '''
def target(x):
    return x + 1

def alternate(x):
    return x - 1

def caller(x):
    note = "target"
    return target(x)
''',
    )

    assert repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=2,
        seed=0,
    ) == []


def test_default_argument_requirements_are_controlled(tmp_path):
    _write(
        tmp_path,
        """
def target(a, b=1):
    return a + b

def same_shape(x, y=2):
    return x * y

def both_required(a, b):
    return a - b

def caller(a):
    return target(a)
""",
    )

    examples = repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=2,
        seed=0,
    )

    assert len(examples) == 1
    assert _candidate_names(examples[0]) == {"target", "same_shape"}


def test_async_status_is_controlled(tmp_path):
    _write(
        tmp_path,
        """
async def target(x):
    return x + 1

async def same_shape(x):
    return x * 2

def sync_shape(x):
    return x - 1

async def caller(x):
    return await target(x)
""",
    )

    examples = repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=2,
        seed=0,
    )

    assert len(examples) == 1
    assert _candidate_names(examples[0]) == {"target", "same_shape"}
    assert all("async def" in candidate for candidate in examples[0].candidates)
