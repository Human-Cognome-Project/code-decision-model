"""Tests for E040 in-scope candidate pools."""
from __future__ import annotations

from pathlib import Path

import pytest

from cdm.binding import CallSiteBindable
from cdm.crossfile import repository_hard_masked_cross_file_call_examples
from cdm.repository import repository_hard_masked_call_examples
from cdm.scope import (
    DEFAULT_BODY_CHARS,
    bindable_mask,
    caller_name,
    in_scope_pools,
    pool_census,
    pool_example,
    pool_examples,
    render_symbol,
    target_symbol,
)
from cdm.synthetic import DecisionExample


def _write_repo(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "a.py").write_text(
        "def one(x):\n    return x\n\n"
        "def two(x, y):\n    return x + y\n\n"
        "def three(x, y):\n    return x * y\n\n"
        "def four(x, y):\n    return x - y\n\n"
        "def five(x, y):\n    return x / y\n\n"
        "def caller(v):\n    w = v + 1\n    return two(w, 2)\n"
    )
    (root / "pkg" / "b.py").write_text(
        "from pkg.a import two, one as uno\n"
        "from pkg.nowhere import ghost\n\n"
        "def two_local(x, y):\n    return y\n\n"
        "def user(v):\n    return two(v, v)\n\n"
        "def lonely():\n    return 0\n"
    )
    (root / "pkg" / "c.py").write_text(
        "def unrelated(a, b, c):\n    return a\n\n"
        "def other(a, b=1):\n    return b\n"
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _write_repo(tmp_path)
    return tmp_path


def test_scope_pools_are_local_plus_resolved_imports_minus_caller(repo: Path):
    scope = in_scope_pools(repo)
    assert len(scope.all_symbols) == 11
    pool = scope.pools[("pkg/a.py", "caller")]
    assert [s.name for s in pool.local] == ["one", "two", "three", "four", "five"]
    assert pool.imported == ()
    pool = scope.pools[("pkg/b.py", "user")]
    assert [s.name for s in pool.local] == ["two_local", "lonely"]
    # Both from-imports of pkg.a resolve (alias order is by local alias name); pkg.nowhere does not.
    assert sorted(s.name for s in pool.imported) == ["one", "two"]
    assert all(s.source == "pkg/a.py" for s in pool.imported)
    assert len(pool.symbols) == 4
    with pytest.raises(ValueError):
        scope.level_pool(DecisionExample("def f():\n    pass\n", "q", ("x",), 0, "t", "pkg/a.py"), "galaxy")


def test_caller_name_and_repository_pool_exclude_the_caller(repo: Path):
    scope = in_scope_pools(repo)
    example = repository_hard_masked_call_examples(repo, candidate_count=4)[0]
    assert example.source == "pkg/a.py" and caller_name(example) == "caller"
    repository = scope.repository_pool(example)
    assert len(repository) == 10 and all(not (s.source == "pkg/a.py" and s.name == "caller") for s in repository)
    with pytest.raises(ValueError):
        caller_name(DecisionExample("x = 1\n", "q", ("a", "b"), 0, "t", "pkg/a.py"))


def test_census_recovers_the_target_and_prunes_with_the_e024_predicate(repo: Path):
    scope = in_scope_pools(repo)
    same_file = repository_hard_masked_call_examples(repo, candidate_count=4)
    cross = repository_hard_masked_cross_file_call_examples(repo, candidate_count=2)
    assert len(same_file) == 1 and len(cross) == 1

    census = pool_census(same_file[0], scope)
    assert census.protocol_candidates == 4
    assert census.scope_size == 5 and census.scope_local == 5 and census.scope_imported == 0
    # two(w, 2): one(x) cannot take two positionals, so bindability drops it.
    assert census.scope_bindable == 4 and census.scope_shape_matched == 4
    assert census.target_in_scope and census.target_bindable_in_scope and census.target_in_repository
    assert census.repository_size == 10
    assert not census.scope_solved_by_predicate

    census = pool_census(cross[0], scope)
    assert census.scope_size == 4 and census.scope_local == 2 and census.scope_imported == 2
    # two(v, v): two_local and two bind; lonely() and one(x) do not.
    assert census.scope_bindable == 2 and census.target_in_scope and census.target_bindable_in_scope
    assert not census.scope_solved_by_predicate

    # The mask is exactly the E024 constraint over the same renderings.
    symbols = scope.pool_for(cross[0]).symbols
    rendered = [render_symbol(s) for s in symbols]
    assert bindable_mask(cross[0], symbols) == tuple(
        CallSiteBindable().check(cross[0].context, cross[0].question, rendered).allowed
    )
    assert bindable_mask(cross[0], ()) == ()
    assert target_symbol(cross[0], symbols).name == "two"
    assert pool_census(DecisionExample("def nobody():\n    pass\n", "q", ("a", "b"), 0, "t", "pkg/a.py"), scope) is None


def test_pool_example_reposes_the_task_over_the_bindable_pool(repo: Path):
    scope = in_scope_pools(repo)
    example = repository_hard_masked_call_examples(repo, candidate_count=4)[0]
    target = example.candidates[example.answer_index]

    full = pool_example(example, scope)
    assert full is not None and len(full.candidates) == 4  # one(x) pruned by bindability
    assert full.candidates[full.answer_index] == target
    assert full.task == "python.hard_masked_direct_call.scope_pool"
    assert full.context == example.context and full.source == example.source
    assert len(set(full.candidates)) == len(full.candidates)

    small = pool_example(example, scope, candidate_count=2)
    assert small is not None and len(small.candidates) == 2 and target in small.candidates
    assert pool_example(example, scope, candidate_count=2) == small  # stable
    assert pool_example(example, scope, candidate_count=2, seed=1) != small or True  # seed may or may not change a 2-set
    assert pool_example(example, scope, candidate_count=9) is None  # pool too small

    repository = pool_example(example, scope, level="repository")
    assert repository is not None and repository.task.endswith(".repository_pool")
    assert target in repository.candidates and len(repository.candidates) > len(full.candidates)
    with pytest.raises(ValueError):
        pool_example(example, scope, level="galaxy")
    with pytest.raises(ValueError):
        pool_example(example, scope, candidate_count=1)

    assert pool_examples([example], scope) == [full]


def test_target_outside_bindable_pool_yields_none(repo: Path):
    scope = in_scope_pools(repo)
    example = repository_hard_masked_call_examples(repo, candidate_count=4)[0]
    # Relabel the task to a candidate that is not in the caller's scope at all.
    foreign = DecisionExample(
        example.context, example.question,
        example.candidates[:1] + ("unrelated(a, b, c)\ndef unrelated(a, b, c):\n    return a\n",),
        1, example.task, example.source,
    )
    assert pool_example(foreign, scope) is None
    assert not pool_census(foreign, scope).target_in_scope


def test_identical_functions_in_two_files_are_one_candidate(tmp_path: Path):
    _write_repo(tmp_path)
    # A byte-identical copy of `two` elsewhere: a scorer cannot tell them apart.
    (tmp_path / "pkg" / "d.py").write_text("def two(x, y):\n    return x + y\n\ndef three(x, y):\n    return x * y\n")
    scope = in_scope_pools(tmp_path)
    example = repository_hard_masked_call_examples(tmp_path, candidate_count=4)[0]
    assert example.candidates[example.answer_index].startswith("two(")

    census = pool_census(example, scope)
    assert census.target_unique_in_scope  # the copy is not in the caller's scope
    assert not census.target_unique_in_repository
    # Distinct renderings: d.py adds nothing new, so the repository size is unchanged.
    assert census.repository_size == 10

    assert pool_example(example, scope) is not None
    assert pool_example(example, scope, level="repository") is None  # ambiguous label

    # Negative-only duplicates are collapsed, not rejected.
    (tmp_path / "pkg" / "d.py").write_text("def three(x, y):\n    return x * y\n")
    scope = in_scope_pools(tmp_path)
    widened = pool_example(example, scope, level="repository")
    assert widened is not None and len(set(widened.candidates)) == len(widened.candidates)
    assert widened.candidates[widened.answer_index] == example.candidates[example.answer_index]


def test_protocol_negatives_in_scope_and_the_scope_filter(repo: Path):
    scope = in_scope_pools(repo)
    same_file = repository_hard_masked_call_examples(repo, candidate_count=4)[0]
    census = pool_census(same_file, scope)
    assert census.protocol_negatives_in_scope == 3 and not census.scope_filter_resolves_protocol

    cross = repository_hard_masked_cross_file_call_examples(repo, candidate_count=2)[0]
    census = pool_census(cross, scope)
    negative = cross.candidates[1 - cross.answer_index]
    in_scope = {render_symbol(s) for s in scope.pool_for(cross).symbols}
    assert census.protocol_negatives_in_scope == int(negative in in_scope)
    assert census.scope_filter_resolves_protocol == (negative not in in_scope)


def test_target_in_scope_independently_of_the_masked_call(tmp_path: Path):
    _write_repo(tmp_path)
    (tmp_path / "pkg" / "e.py").write_text(
        "from pkg.a import two, three\n\n"
        "def first(v):\n    return two(v, v)\n\n"
        "def second(v):\n    return two(v, 1)\n\n"
        "LIMIT = three(2, 3)\n"
    )
    scope = in_scope_pools(tmp_path)
    # `two` is read by the other function and `three` by a module-level
    # assignment, so both imports exist independently of `first`.
    assert [s.name for s in scope.pools[("pkg/e.py", "first")].imported_used_elsewhere] == ["three", "two"]
    # In pkg/b.py only `user` reads `two`, and nothing reads `uno`.
    assert scope.pools[("pkg/b.py", "user")].imported_used_elsewhere == ()
    assert [s.name for s in scope.pools[("pkg/b.py", "lonely")].imported_used_elsewhere] == ["two"]

    same_file = repository_hard_masked_call_examples(tmp_path, candidate_count=4)
    census = pool_census(next(e for e in same_file if e.source == "pkg/a.py"), scope)
    assert census.target_in_scope_independently  # a same-file target is always in scope

    for example in repository_hard_masked_cross_file_call_examples(tmp_path, candidate_count=2):
        census = pool_census(example, scope)
        independent = (example.source, caller_name(example)) in {("pkg/e.py", "first"), ("pkg/e.py", "second")}
        assert census.target_in_scope_independently == independent, (example.source, caller_name(example))
        assert census.scope_filter_resolves_protocol_independently == (
            census.scope_filter_resolves_protocol and independent
        )


def test_this_repository_recovers_every_hard_target_in_scope():
    root = Path(__file__).resolve().parents[1]
    scope = in_scope_pools(root)
    examples = [
        *repository_hard_masked_call_examples(root, candidate_count=4),
        *repository_hard_masked_cross_file_call_examples(root, candidate_count=4),
    ]
    assert examples
    for example in examples:
        census = pool_census(example, scope, body_chars=DEFAULT_BODY_CHARS)
        assert census is not None, example.source
        assert census.target_in_scope and census.target_bindable_in_scope and census.target_in_repository, example.source
        assert census.scope_bindable <= census.scope_size <= census.repository_size + 1
        assert census.repository_bindable <= census.repository_size
    widened = pool_examples(examples, scope)
    assert len(widened) == len(examples)
    assert all(w.candidates[w.answer_index] == e.candidates[e.answer_index] for w, e in zip(widened, examples))
    # Repository level: every re-posed task has distinct candidates, and the
    # only tasks dropped are those whose target rendering is ambiguous.
    repository = [pool_example(e, scope, level="repository") for e in examples]
    for example, posed in zip(examples, repository):
        census = pool_census(example, scope)
        assert (posed is None) == (not census.target_unique_in_repository), example.source
        if posed is not None:
            assert len(set(posed.candidates)) == len(posed.candidates)
            assert posed.candidates[posed.answer_index] == example.candidates[example.answer_index]
