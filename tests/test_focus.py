from cdm.focus import focus_hard_call_context
from cdm.synthetic import DecisionExample


def _example(context):
    return DecisionExample(
        context=context,
        question="Which candidate replaces __CALL_TARGET__?",
        candidates=("a", "b"),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="repo::module.py",
    )


def test_focus_keeps_header_marker_and_local_window():
    example = _example(
        """def caller(x):
    a = x + 1
    b = a + 1
    c = b + 1
    d = c + 1
    value = __CALL_TARGET__(d)
    e = value + 1
    f = e + 1
    g = f + 1
    return g
"""
    )

    focused = focus_hard_call_context(example, radius_lines=1)

    assert focused.context.startswith("def caller(x):")
    assert "__CALL_TARGET__" in focused.context
    assert "d = c + 1" in focused.context
    assert "e = value + 1" in focused.context
    assert "a = x + 1" not in focused.context
    assert "return g" not in focused.context
    assert "omitted before" in focused.context
    assert "omitted after" in focused.context
    assert focused.candidates == example.candidates
    assert focused.answer_index == example.answer_index


def test_focus_returns_short_context_exactly():
    example = _example(
        """def caller(x):
    return __CALL_TARGET__(x)
"""
    )

    focused = focus_hard_call_context(example, radius_lines=8)
    assert focused == example


def test_focus_handles_async_and_decorator_prefix():
    example = _example(
        """@decorator
async def caller(x):
    a = x + 1
    b = a + 1
    return await __CALL_TARGET__(b)
"""
    )

    focused = focus_hard_call_context(example, radius_lines=0)

    assert focused.context.startswith("@decorator\nasync def caller(x):")
    assert "return await __CALL_TARGET__(b)" in focused.context
    assert "a = x + 1" not in focused.context


def test_focus_spans_multiple_marker_occurrences():
    example = _example(
        """def caller(x):
    a = x + 1
    first = __CALL_TARGET__(a)
    middle = first + 1
    second = __CALL_TARGET__(middle)
    return second
"""
    )

    focused = focus_hard_call_context(example, radius_lines=0)
    assert focused.context.count("__CALL_TARGET__") == 2
    assert "middle = first + 1" in focused.context


def test_focus_validates_task_radius_and_marker():
    wrong = DecisionExample(
        context="def f():\n    return 1",
        question="q",
        candidates=("a", "b"),
        answer_index=0,
        task="other",
        source="repo::x.py",
    )
    try:
        focus_hard_call_context(wrong)
    except ValueError as exc:
        assert "hard masked-call" in str(exc)
    else:
        raise AssertionError("expected task validation")

    example = _example("def caller(x):\n    return __CALL_TARGET__(x)")
    try:
        focus_hard_call_context(example, radius_lines=-1)
    except ValueError as exc:
        assert "radius_lines" in str(exc)
    else:
        raise AssertionError("expected radius validation")


def test_focus_supports_hard_masked_method_calls():
    example = DecisionExample(
        context="""def caller(self, x):
    a = x + 1
    b = a + 1
    value = self.__CALL_TARGET__(b)
    c = value + 1
    return c
""",
        question="Which candidate method replaces __CALL_TARGET__?",
        candidates=("target(self, x)", "other(self, x)"),
        answer_index=0,
        task="python.hard_masked_same_class_call",
        source="repo::module.py",
    )

    focused = focus_hard_call_context(example, radius_lines=0)

    assert focused.context.startswith("def caller(self, x):")
    assert "self.__CALL_TARGET__(b)" in focused.context
    assert "a = x + 1" not in focused.context
    assert "return c" not in focused.context
    assert focused.candidates == example.candidates
    assert focused.answer_index == example.answer_index
