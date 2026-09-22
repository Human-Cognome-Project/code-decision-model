import ast

from cdm.repository import repository_hard_masked_call_examples


SOURCE = """
def normalize(x):
    return x.strip().lower()

def parse_number(x):
    return int(x)

def clamp(x):
    return max(0, min(100, x))

def emit(x):
    return str(x)

def encode(x):
    return bytes(str(x), "utf-8")

def clean_user_input(x):
    value = normalize(x)
    return value or "missing"

def load_count(x):
    value = parse_number(x)
    return value + 1
"""


def _write_repo(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "pipeline.py").write_text(SOURCE, encoding="utf-8")


def _candidate_arity(candidate):
    signature = candidate.split("\n", 1)[0]
    inside = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if not inside:
        return 0
    return sum(1 for part in inside.split(",") if not part.strip().startswith("*"))


def test_hard_masked_candidates_control_path_and_arity_shortcuts(tmp_path):
    _write_repo(tmp_path)

    examples = repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=4,
        seed=13,
    )

    assert len(examples) == 2
    for example in examples:
        assert example.task == "python.hard_masked_direct_call"
        assert "__CALL_TARGET__" in example.context
        assert "file:" not in example.context
        assert all("pkg/" not in candidate for candidate in example.candidates)
        assert len(example.candidates) == 4

        arities = {_candidate_arity(candidate) for candidate in example.candidates}
        assert len(arities) == 1

        code = ast.parse(example.context)
        assert not any(
            isinstance(node, ast.Name) and node.id in {"normalize", "parse_number"}
            for node in ast.walk(code)
            if isinstance(node, ast.Name) and node.id != "__CALL_TARGET__"
        )


def test_hard_masked_pool_excludes_caller_definition(tmp_path):
    _write_repo(tmp_path)
    examples = repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=4,
        seed=2,
    )

    clean = next(e for e in examples if "clean_user_input" in e.context)
    assert all(not candidate.startswith("clean_user_input(") for candidate in clean.candidates)

    load = next(e for e in examples if "load_count" in e.context)
    assert all(not candidate.startswith("load_count(") for candidate in load.candidates)


def test_hard_masked_examples_require_full_candidate_count(tmp_path):
    _write_repo(tmp_path)

    # Excluding the caller leaves only six one-argument candidates.
    assert repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=7,
        seed=0,
    ) == []


def test_hard_masked_candidate_order_is_seeded(tmp_path):
    _write_repo(tmp_path)

    a = repository_hard_masked_call_examples(tmp_path, candidate_count=4, seed=7)
    b = repository_hard_masked_call_examples(tmp_path, candidate_count=4, seed=7)
    c = repository_hard_masked_call_examples(tmp_path, candidate_count=4, seed=8)

    assert a == b
    assert any(x.candidates != y.candidates for x, y in zip(a, c))
