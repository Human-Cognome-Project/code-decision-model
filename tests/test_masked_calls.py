import ast

from cdm.repository import (
    repository_call_examples,
    repository_masked_call_examples,
)


SOURCE = """
def normalize(x):
    return x.strip().lower()

def parse_number(x):
    return int(x)

def clamp(x):
    return max(0, min(100, x))

def clean_user_input(x):
    value = normalize(x)
    return value or "missing"

def load_count(x):
    value = parse_number(x)
    return value + 1

def safe_percent(x):
    value = clamp(x)
    return f"{value}%"
"""


def _write_repo(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "pipeline.py").write_text(SOURCE, encoding="utf-8")
    (pkg / "other.py").write_text(
        """
def emit_json(x):
    return {"value": x}

def archive(x):
    return bytes(str(x), "utf-8")
""",
        encoding="utf-8",
    )


def test_masked_call_examples_remove_executable_target_name(tmp_path):
    _write_repo(tmp_path)

    examples = repository_masked_call_examples(
        tmp_path,
        max_candidates=5,
        seed=11,
    )

    assert len(examples) == 3
    assert all(e.task == "python.masked_direct_call" for e in examples)
    assert all("__CALL_TARGET__" in e.context for e in examples)

    for example in examples:
        code = example.context.split("\n\n", 1)[1]
        tree = ast.parse(code)
        target_candidate = example.candidates[example.answer_index]
        target_name = target_candidate.split("::", 1)[1].split("(", 1)[0]

        assert not any(
            isinstance(node, ast.Name) and node.id == target_name
            for node in ast.walk(tree)
        )
        assert target_name in target_candidate


def test_masked_candidates_include_implementation_context(tmp_path):
    _write_repo(tmp_path)
    examples = repository_masked_call_examples(
        tmp_path,
        max_candidates=5,
        candidate_body_chars=512,
        seed=7,
    )

    assert examples
    assert all("\ndef " in candidate for e in examples for candidate in e.candidates)


def test_masking_preserves_machine_verified_example_count(tmp_path):
    _write_repo(tmp_path)

    direct = repository_call_examples(tmp_path, max_candidates=5, seed=3)
    masked = repository_masked_call_examples(tmp_path, max_candidates=5, seed=3)

    assert len(masked) == len(direct) == 3


def test_masked_candidate_order_is_deterministic_but_seeded(tmp_path):
    _write_repo(tmp_path)

    a = repository_masked_call_examples(tmp_path, max_candidates=5, seed=1)
    b = repository_masked_call_examples(tmp_path, max_candidates=5, seed=1)
    c = repository_masked_call_examples(tmp_path, max_candidates=5, seed=2)

    assert a == b
    assert any(x.candidates != y.candidates for x, y in zip(a, c))
