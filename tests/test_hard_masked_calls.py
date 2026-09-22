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


def _candidate_shape(candidate):
    signature = candidate.split("\n", 1)[0]
    fn = ast.parse(f"def {signature}:\n    pass\n").body[0]
    return (
        len(fn.args.posonlyargs) + len(fn.args.args),
        len(fn.args.kwonlyargs),
        fn.args.vararg is not None,
        fn.args.kwarg is not None,
    )


def test_hard_masked_candidates_control_path_and_call_shape_shortcuts(tmp_path):
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

        shapes = {_candidate_shape(candidate) for candidate in example.candidates}
        assert len(shapes) == 1

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


def test_hard_masked_call_shape_comes_from_ast_categories(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "shapes.py").write_text(
        """
def target(a, /, b, *, c):
    return a + b + c

def same_shape(x, /, y, *, z):
    return x * y + z

def wrong_plain(a, b, c):
    return a - b - c

def wrong_vararg(a, b, *rest):
    return a + b + len(rest)

def caller(a, b, c):
    return target(a, b, c=c)
""",
        encoding="utf-8",
    )

    examples = repository_hard_masked_call_examples(
        tmp_path,
        candidate_count=2,
        seed=0,
    )

    assert len(examples) == 1
    names = {
        candidate.split("(", 1)[0]
        for candidate in examples[0].candidates
    }
    assert names == {"target", "same_shape"}
    assert {_candidate_shape(c) for c in examples[0].candidates} == {
        (2, 1, False, False)
    }
