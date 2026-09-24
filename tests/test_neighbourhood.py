"""Tests for E044 import-neighbourhood pools."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.neighbourhood import import_neighbourhoods, neighbourhood_census
from cdm.scope import caller_name
from cdm.synthetic import DecisionExample


def _write_repo(root: Path) -> None:
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text(
        "LIMIT = 3\n\n"
        "def one(x):\n    return x\n\n"
        "def two(x, y):\n    return x + y\n\n"
        "def three(x, y):\n    return x * y\n"
    )
    (pkg / "b.py").write_text(
        "def four(x, y):\n    return x - y\n\n"
        "def five(x):\n    return -x\n"
    )
    (pkg / "c.py").write_text("def six(x, y):\n    return y\n")
    (pkg / "user.py").write_text(
        "from pkg.a import two, three\n"
        "from pkg.b import four\n"
        "import pkg.c\n\n"
        "def caller(v):\n    return two(v, v)\n\n"
        "def other(v):\n    return three(v, 1)\n"
    )
    (pkg / "solo.py").write_text(
        "from pkg.b import five\n\n"
        "def lonely(v):\n    return five(v)\n"
    )
    (pkg / "dep.py").write_text(
        "from pkg.a import two, LIMIT\n\n"
        "def uses(v):\n    return two(v, LIMIT)\n"
    )
    (pkg / "star.py").write_text(
        "from pkg.b import *\n"
        "from pkg.b import four\n\n"
        "def starry(v):\n    return four(v, v)\n"
    )
    (pkg / "rel.py").write_text(
        "from . import c\n"
        "from .b import five\n\n"
        "def near(v):\n    return five(v)\n\n"
        "def far(v):\n    return c.six(v, v)\n"
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _write_repo(tmp_path)
    return tmp_path


def _tasks(repo: Path) -> dict[tuple[str, str], DecisionExample]:
    examples = repository_hard_masked_cross_file_call_examples(repo, candidate_count=2)
    return {(e.source, caller_name(e)): e for e in examples}


def test_the_fixture_yields_the_intended_cross_file_tasks(repo: Path):
    assert set(_tasks(repo)) == {
        ("pkg/user.py", "caller"),
        ("pkg/user.py", "other"),
        ("pkg/solo.py", "lonely"),
        ("pkg/dep.py", "uses"),
        ("pkg/star.py", "starry"),
        ("pkg/rel.py", "near"),
    }


def test_alias_variant_removes_only_the_target_name(repo: Path):
    nb = import_neighbourhoods(repo)
    tasks = _tasks(repo)
    caller = tasks[("pkg/user.py", "caller")]
    assert nb.target_aliases(caller) == {"two"}
    # three keeps pkg/a.py, four gives pkg/b.py, `import pkg.c` gives pkg/c.py.
    assert set(nb.neighbourhood_files(caller)) == {"pkg/a.py", "pkg/b.py", "pkg/c.py"}
    assert neighbourhood_census(caller, nb).target_in_alias_pool

    # The target's module is imported for nothing else: a miss by construction.
    lonely = tasks[("pkg/solo.py", "lonely")]
    assert nb.neighbourhood_files(lonely) == ()
    census = neighbourhood_census(lonely, nb)
    assert not census.target_in_alias_pool and census.alias_bindable == 0
    assert census.alias_uniform_recall == 0.0


def test_independent_variant_keeps_only_names_read_outside_the_caller(repo: Path):
    nb = import_neighbourhoods(repo)
    tasks = _tasks(repo)
    caller = tasks[("pkg/user.py", "caller")]
    # three is read by `other`; four and pkg are read by nothing else.
    assert nb.neighbourhood_files(caller, variant="independent") == ("pkg/a.py",)
    assert neighbourhood_census(caller, nb).target_in_independent_pool

    # LIMIT brings pkg/a.py in, but only the masked caller reads it.
    uses = tasks[("pkg/dep.py", "uses")]
    census = neighbourhood_census(uses, nb)
    assert census.target_in_alias_pool and not census.target_in_independent_pool
    with pytest.raises(ValueError):
        nb.neighbourhood_files(uses, variant="statement")


def test_star_imports_count_only_in_the_primary_variant(repo: Path):
    nb = import_neighbourhoods(repo)
    starry = _tasks(repo)[("pkg/star.py", "starry")]
    assert nb.neighbourhood_files(starry) == ("pkg/b.py",)
    assert nb.neighbourhood_files(starry, variant="independent") == ()
    census = neighbourhood_census(starry, nb)
    assert census.target_in_alias_pool and not census.target_in_independent_pool


def test_relative_and_submodule_imports_resolve(repo: Path):
    nb = import_neighbourhoods(repo)
    near = _tasks(repo)[("pkg/rel.py", "near")]
    # `from . import c` resolves the submodule; `.b` is the target's own import.
    # The empty package __init__ defines no functions, so the shared symbol
    # collection does not list it and it resolves to nothing.
    assert nb.neighbourhood_files(near) == ("pkg/c.py",)
    assert nb.neighbourhood_files(near, variant="independent") == ("pkg/c.py",)
    assert not neighbourhood_census(near, nb).target_in_alias_pool


def test_uniform_recall_and_non_cross_file_tasks(repo: Path):
    nb = import_neighbourhoods(repo)
    caller = _tasks(repo)[("pkg/user.py", "caller")]
    census = neighbourhood_census(caller, nb)
    assert census.target_unique_in_repository
    assert 0 < census.alias_bindable <= census.repository_bindable
    assert census.alias_uniform_recall == census.alias_bindable / census.repository_bindable
    assert all(not (s.source == "pkg/user.py" and s.name == "caller") for s in nb.repository_pool(caller))
    # A task whose target is not bound by any module-level import is not E030.
    local = DecisionExample("def lonely(v):\n    return __CALL_TARGET__(v)\n", "q", ("def one(x)\nreturn x",), 0, "t", "pkg/solo.py")
    assert nb.neighbourhood_files(local) is None and neighbourhood_census(local, nb) is None


def test_this_repository_neighbourhoods_are_consistent():
    root = Path(__file__).resolve().parents[1]
    nb = import_neighbourhoods(root)
    examples = repository_hard_masked_cross_file_call_examples(root, candidate_count=4)
    assert examples
    for example in examples:
        census = neighbourhood_census(example, nb)
        assert census is not None, example.source
        # The strict variant only ever removes modules.
        assert set(nb.neighbourhood_files(example, variant="independent")) <= set(nb.neighbourhood_files(example))
        assert census.independent_bindable <= census.alias_bindable <= census.repository_bindable
        assert census.target_in_alias_pool or not census.target_in_independent_pool
        # The removed names are exactly the ones the E030 context masks.
        aliases = nb.target_aliases(example)
        assert aliases and not any(re.search(rf"\b{re.escape(a)}\b", example.context) for a in aliases)
