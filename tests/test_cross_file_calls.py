"""Tests for import-resolved cross-file call supervision (E030)."""
from __future__ import annotations

import ast

import pytest

from cdm.crossfile import TASK, repository_hard_masked_cross_file_call_examples
from cdm.focus import focus_hard_call_context
from cdm.repair import expected_repair_source, verify_repair
from cdm.structured_edit import verify_selection


LIB = '''
def load(x):
    return x.read()

def parse(x):
    return int(x)

def emit(x):
    return str(x)

def clamp(x):
    return max(0, x)
'''

USER = '''
from pkg.lib import load

def run(v):
    handle = open(v)
    return load(handle)

def helper_a(x):
    return x + 1

def helper_b(x):
    return x - 1
'''


def _write(tmp_path, files: dict[str, str]):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _shape(candidate):
    fn = ast.parse(f"def {candidate.splitlines()[0]}:\n    pass\n").body[0]
    return (
        len(fn.args.posonlyargs) + len(fn.args.args),
        len(fn.args.kwonlyargs),
        fn.args.vararg is not None,
        fn.args.kwarg is not None,
    )


def test_absolute_import_resolves_to_other_file(tmp_path):
    _write(tmp_path, {"pkg/__init__.py": "", "pkg/lib.py": LIB, "pkg/user.py": USER})

    examples = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4)

    assert len(examples) == 1
    example = examples[0]
    assert example.task == TASK
    assert example.source == "pkg/user.py"
    assert "__CALL_TARGET__" in example.context
    assert "load" not in example.context
    assert "import" not in example.context
    assert example.candidates[example.answer_index].startswith("load(x)")
    assert len(example.candidates) == 4
    assert len({_shape(c) for c in example.candidates}) == 1
    assert all(not c.startswith("run(") for c in example.candidates)


def test_relative_and_package_init_imports(tmp_path):
    _write(tmp_path, {
        "pkg/__init__.py": "def boot(x):\n    return x\n\ndef spare(x):\n    return x\n",
        "pkg/lib.py": LIB,
        "pkg/user.py": (
            "from .lib import parse\n"
            "from . import boot\n\n"
            "def one(v):\n    return parse(v)\n\n"
            "def two(v):\n    return boot(v)\n\n"
            "def pad(v):\n    return v\n"
        ),
    })

    examples = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4)
    targets = {
        e.context.split("(", 1)[0].replace("def ", ""): e.candidates[e.answer_index].split("(", 1)[0]
        for e in examples
    }
    assert targets == {"one": "parse", "two": "boot"}


def test_src_layout_resolves_through_source_root(tmp_path):
    _write(tmp_path, {
        "src/pkg/__init__.py": "",
        "src/pkg/lib.py": LIB,
        "src/pkg/user.py": USER,
    })

    examples = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4)
    assert len(examples) == 1
    assert examples[0].source == "src/pkg/user.py"


def test_alias_is_masked_and_real_name_does_not_leak(tmp_path):
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB,
        "pkg/user.py": USER.replace("import load", "import load as fetch").replace("load(handle)", "fetch(handle)"),
    })

    examples = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4)
    assert len(examples) == 1
    context = examples[0].context
    assert "fetch" not in context
    assert "load" not in context
    assert examples[0].candidates[examples[0].answer_index].startswith("load(x)")

    # A leaked real name (e.g. in a docstring) rejects the example.
    _write(tmp_path, {
        "pkg/user.py": USER.replace("import load", "import load as fetch")
        .replace("load(handle)", "fetch(handle)")
        .replace("handle = open(v)", 'handle = open(v)  # uses load\n    """load helper"""'),
    })
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4) == []


def test_non_function_and_unresolvable_imports_are_ignored(tmp_path):
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB + "\nLIMIT = 3\n\nclass Box:\n    pass\n",
        "pkg/user.py": (
            "from pkg.lib import LIMIT, Box\n"
            "from requests import get\n"
            "from pkg.missing import nothing\n\n"
            "def run(v):\n    return get(v) + LIMIT + Box()\n\n"
            "def a(x):\n    return x\n\n"
            "def b(x):\n    return x\n"
        ),
    })
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=2) == []


def test_two_cross_file_targets_and_nested_scopes_are_skipped(tmp_path):
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB,
        "pkg/user.py": (
            "from pkg.lib import load, parse\n\n"
            "def both(v):\n    return load(v) + parse(v)\n\n"
            "def nested(v):\n    def inner():\n        return load(v)\n    return inner\n\n"
            "def clean(v):\n    return parse(v)\n\n"
            "def pad(v):\n    return v\n"
        ),
    })

    examples = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4)
    callers = {e.context.split("(", 1)[0].replace("def ", "") for e in examples}
    assert callers == {"clean"}


def test_shadowed_alias_is_skipped(tmp_path):
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB,
        "pkg/user.py": USER + "\ndef load(x):\n    return x\n",
    })
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4) == []


def test_candidate_count_is_enforced_and_order_is_seeded(tmp_path):
    _write(tmp_path, {"pkg/__init__.py": "", "pkg/lib.py": LIB, "pkg/user.py": USER})

    # load/parse/emit/clamp/helper_a/helper_b share shape: six eligible candidates.
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=7) == []
    a = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4, seed=1)
    b = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4, seed=1)
    assert a == b
    with pytest.raises(ValueError):
        repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=1)


def test_cross_file_examples_work_with_frozen_harnesses(tmp_path):
    _write(tmp_path, {"pkg/__init__.py": "", "pkg/lib.py": LIB, "pkg/user.py": USER})
    example = repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4)[0]

    assert verify_repair(example, expected_repair_source(example)).valid
    assert verify_selection(example, str(example.answer_index + 1)).valid
    assert not verify_selection(example, str((example.answer_index + 1) % 4 + 1)).valid
    assert focus_hard_call_context(example, radius_lines=1).candidates == example.candidates


def test_call_site_predicate_stays_sound_on_this_repository():
    from pathlib import Path

    from cdm.binding import CallSiteBindable

    root = Path(__file__).resolve().parents[1]
    examples = repository_hard_masked_cross_file_call_examples(root, candidate_count=4)
    predicate = CallSiteBindable()
    assert examples
    for example in examples:
        allowed = predicate.check(example.context, example.question, example.candidates).allowed
        assert allowed[example.answer_index], example.source


def test_no_implicit_relative_absolute_import_resolution(tmp_path):
    # Python 3 would not resolve `from lib import load` inside pkg/ to pkg/lib.py.
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB,
        "pkg/user.py": USER.replace("from pkg.lib import load", "from lib import load"),
    })
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4) == []


def test_ambiguous_absolute_imports_are_skipped(tmp_path):
    # The same module path exists under the repository root and under src/.
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB,
        "src/pkg/__init__.py": "",
        "src/pkg/lib.py": LIB,
        "pkg/user.py": USER,
    })
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4) == []

    # Both pkg/lib.py and pkg/lib/__init__.py exist.
    _write(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/lib.py": LIB,
        "pkg/lib/__init__.py": LIB,
        "pkg/user.py": USER,
    })
    import shutil
    shutil.rmtree(tmp_path / "src")
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4) == []


def test_source_roots_are_explicit(tmp_path):
    _write(tmp_path, {
        "lib_root/pkg/__init__.py": "",
        "lib_root/pkg/lib.py": LIB,
        "lib_root/pkg/user.py": USER,
    })
    # Not a supported root by default, so the import does not resolve.
    assert repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=4) == []
    declared = repository_hard_masked_cross_file_call_examples(
        tmp_path, candidate_count=4, source_roots=("lib_root",)
    )
    assert len(declared) == 1
    assert declared[0].source == "lib_root/pkg/user.py"
