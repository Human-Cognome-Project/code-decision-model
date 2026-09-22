"""Tests for the deterministic call-site bindability predicate (E023)."""
from __future__ import annotations

from pathlib import Path

import torch

from cdm.binding import (
    CallShape,
    CallSiteBindable,
    binds,
    call_shapes,
    candidate_parameters,
)
from cdm.constraints import apply_constraints
from cdm.methods import repository_hard_masked_method_call_examples
from cdm.repository import (
    repository_hard_masked_call_examples,
    repository_masked_call_examples,
)


def _shape(
    positional=0,
    keywords=(),
    *,
    starred=False,
    double_starred=False,
    receiver=False,
) -> CallShape:
    return CallShape(
        positional=positional,
        keywords=frozenset(keywords),
        starred=starred,
        double_starred=double_starred,
        receiver=receiver,
    )


def _params(header: str):
    return candidate_parameters(f"sig()\ndef {header}:\n    pass\n")


def test_call_shapes_read_name_and_attribute_calls():
    shapes = call_shapes(
        "def f(self, x, *rest, **opts):\n"
        "    a = __CALL_TARGET__(x, 1, key=2)\n"
        "    b = self.__CALL_TARGET__(*rest, **opts)\n"
        "    return a, b\n"
    )
    assert shapes == (
        _shape(2, {"key"}),
        _shape(0, (), starred=True, double_starred=True, receiver=True),
    )


def test_call_shapes_ignore_unparseable_or_uncalled_marker():
    assert call_shapes("def f(:\n") == ()
    assert call_shapes("def f(x):\n    return __CALL_TARGET__\n") == ()


def test_candidate_parameters_use_body_defaults_when_present():
    params = candidate_parameters(
        "pkg/mod.py::f(a, b, /, c, *, d, e)\n"
        "def f(a, b=1, /, c=2, *, d, e=3):\n"
        "    return a\n"
    )
    assert params.positional_only == ("a", "b")
    assert params.positional_or_keyword == ("c",)
    assert params.keyword_only == ("d", "e")
    assert params.required == {"a", "d"}
    assert params.defaults_known


def test_candidate_parameters_treat_unknown_defaults_as_optional():
    params = candidate_parameters("f(a, b, *, c)")
    assert params.required == frozenset()
    assert not params.defaults_known
    assert params.positional_or_keyword == ("a", "b")
    assert params.keyword_only == ("c",)


def test_candidate_parameters_survive_truncated_body():
    truncated = "f(a, b)\ndef f(a, b=1):\n    return a + (b"
    params = candidate_parameters(truncated)
    assert params.defaults_known
    assert params.required == {"a"}

    # Truncated inside the header falls back to the signature line.
    params = candidate_parameters("f(a, b)\ndef f(a, b=[1,")
    assert not params.defaults_known
    assert params.positional_or_keyword == ("a", "b")


def test_binds_positional_capacity():
    assert binds(_params("f(a, b)"), _shape(2))
    assert not binds(_params("f(a, b)"), _shape(3))
    assert binds(_params("f(a, *rest)"), _shape(3))


def test_binds_required_parameters():
    assert not binds(_params("f(a, b)"), _shape(1))
    assert binds(_params("f(a, b=1)"), _shape(1))
    assert binds(_params("f(a, b)"), _shape(1, {"b"}))
    assert not binds(_params("f(a, *, k)"), _shape(1))
    assert binds(_params("f(a, *, k)"), _shape(1, {"k"}))


def test_binds_keyword_rules():
    assert not binds(_params("f(a, b)"), _shape(1, {"zzz"}))
    assert binds(_params("f(a, **kw)"), _shape(1, {"zzz"}))
    assert not binds(_params("f(a, /)"), _shape(0, {"a"}))
    assert not binds(_params("f(a, b)"), _shape(2, {"b"}))


def test_binds_never_vetoes_on_unknown_call_arguments():
    # *args could supply any number of positionals; **kw any keyword.
    assert binds(_params("f(a, b, c)"), _shape(0, (), starred=True))
    assert binds(_params("f(a, *, k)"), _shape(1, (), double_starred=True))
    assert binds(_params("f(a, /, b)"), _shape(1, (), double_starred=True))
    assert not binds(_params("f(a, b, /)"), _shape(1, (), double_starred=True))
    # Known positionals still bound capacity from below.
    assert not binds(_params("f(a)"), _shape(2, (), starred=True))


def test_receiver_calls_accept_bound_or_static_readings():
    predicate = CallSiteBindable()
    context = "def caller(self, value):\n    return self.__CALL_TARGET__(value)\n"
    result = predicate.check(
        context,
        "q",
        (
            "bound(self, value)\ndef bound(self, value):\n    pass\n",
            "static(value)\ndef static(value):\n    pass\n",
            "wide(self, value, extra)\ndef wide(self, value, extra):\n    pass\n",
            "nothing()\ndef nothing():\n    pass\n",
        ),
    )
    assert result.allowed == (True, True, False, False)


def test_predicate_allows_everything_without_call_site_information():
    predicate = CallSiteBindable()
    candidates = ("f(a)", "g(a, b)")
    assert predicate.check("not python (", "q", candidates).allowed == (True, True)
    assert predicate.check("x = 1", "q", candidates).allowed == (True, True)
    assert predicate.check(
        "def f(x):\n    return __CALL_TARGET__(x)\n",
        "q",
        ("??? not a signature",),
    ).allowed == (True,)


def test_predicate_every_call_site_must_bind():
    predicate = CallSiteBindable()
    context = (
        "def caller(x):\n"
        "    first = __CALL_TARGET__(x)\n"
        "    return __CALL_TARGET__(x, x)\n"
    )
    result = predicate.check(
        context,
        "q",
        (
            "one(a)\ndef one(a):\n    pass\n",
            "flex(a, b=None)\ndef flex(a, b=None):\n    pass\n",
        ),
    )
    assert result.allowed == (False, True)


def test_predicate_composes_with_apply_constraints():
    scores = torch.tensor([5.0, 1.0])
    context = "def caller(x):\n    return __CALL_TARGET__(x, mode=1)\n"
    result = apply_constraints(
        scores,
        context,
        "q",
        ("a(x)\ndef a(x):\n    pass\n", "b(x, mode)\ndef b(x, mode=0):\n    pass\n"),
        [CallSiteBindable()],
    )
    assert result.allowed == (False, True)
    assert result.chosen_index == 1
    assert result.reasons[0] != ""
    assert not result.escalate


FIXTURE = '''
def one(x):
    return x

def one_default(x, y=1):
    return x + y

def two(x, y):
    return x * y

def kw_only(x, *, flag):
    return x if flag else None

def variadic(*items, **options):
    return items, options

def pos_only(x, /):
    return x

def use_one(v):
    return one(v)

def use_two(v):
    return two(v, v)

def use_kw(v):
    return kw_only(v, flag=True)

def use_variadic(v):
    return variadic(v, v, v, extra=1)

def use_pos_only(v):
    return pos_only(v)


class Box:
    def __init__(self, value):
        self.value = value

    def plain(self, v):
        return v

    def with_default(self, v, w=0):
        return v + w

    def pair(self, v, w):
        return v - w

    @staticmethod
    def static_one(v):
        return v

    @classmethod
    def make(cls, v):
        return cls(v)

    def use_plain(self, v):
        return self.plain(v)

    def use_pair(self, v):
        return self.pair(v, v)

    def use_static(self, v):
        return self.static_one(v)

    def use_make(self, v):
        return self.make(v)
'''


def _corpora(root: Path):
    return (
        repository_masked_call_examples(root, max_candidates=16),
        repository_hard_masked_call_examples(root, candidate_count=2),
        repository_hard_masked_method_call_examples(root, candidate_count=2),
    )


def _assert_sound(examples):
    predicate = CallSiteBindable()
    assert examples
    for example in examples:
        result = predicate.check(
            example.context, example.question, example.candidates
        )
        assert result.allowed[example.answer_index], (
            example.source,
            example.context,
            example.candidates[example.answer_index],
        )


def test_predicate_is_sound_on_fixture_corpora(tmp_path):
    (tmp_path / "shapes.py").write_text(FIXTURE, encoding="utf-8")
    easy, hard_functions, hard_methods = _corpora(tmp_path)
    _assert_sound(easy)
    _assert_sound(hard_functions)
    _assert_sound(hard_methods)


def test_predicate_prunes_repository_wide_pools_but_not_shape_controlled_ones(tmp_path):
    (tmp_path / "shapes.py").write_text(FIXTURE, encoding="utf-8")
    easy, hard_functions, hard_methods = _corpora(tmp_path)
    predicate = CallSiteBindable()

    def touched(examples):
        return sum(
            sum(predicate.check(e.context, e.question, e.candidates).allowed)
            < len(e.candidates)
            for e in examples
        )

    assert touched(easy) > 0
    # Shape-controlled candidates share the target's binding shape, so the
    # predicate carries no information there by construction.
    assert touched(hard_functions) == 0
    assert touched(hard_methods) == 0


def test_predicate_is_sound_on_this_repository():
    root = Path(__file__).resolve().parents[1]
    easy, hard_functions, hard_methods = _corpora(root)
    _assert_sound(easy)
    _assert_sound(hard_functions)
    _assert_sound(hard_methods)
