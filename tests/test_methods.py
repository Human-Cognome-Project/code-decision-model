import ast

from cdm.methods import repository_hard_masked_method_call_examples


BASIC = """
class Pipeline:
    def normalize(self, x):
        return x.strip().lower()

    def parse(self, x):
        return int(x)

    def clamp(self, x):
        return max(0, min(100, x))

    def emit(self, x):
        return str(x)

    def stage_one(self, x):
        value = self.normalize(x)
        return value or "missing"

    def stage_two(self, x):
        value = self.parse(x)
        return value + 1
"""


def _write(tmp_path, text=BASIC):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "pipeline.py").write_text(text, encoding="utf-8")


def test_same_class_method_targets_are_masked_and_machine_labeled(tmp_path):
    _write(tmp_path)
    examples = repository_hard_masked_method_call_examples(
        tmp_path, candidate_count=4, seed=7
    )
    assert len(examples) == 2
    for example in examples:
        assert example.task == "python.hard_masked_same_class_call"
        assert "__CALL_TARGET__" in example.context
        assert len(example.candidates) == 4
        target = example.candidates[example.answer_index].split("(", 1)[0]
        tree = ast.parse(example.context)
        assert not any(
            isinstance(n, ast.Attribute) and n.attr == target
            for n in ast.walk(tree)
        )


def test_nested_function_calls_do_not_label_outer_method(tmp_path):
    _write(tmp_path, """
class Pipeline:
    def normalize(self, x):
        return x.strip()

    def parse(self, x):
        return int(x)

    def clamp(self, x):
        return max(0, x)

    def emit(self, x):
        return str(x)

    def caller(self, x):
        def inner():
            return self.normalize(x)
        return inner()
""")
    assert repository_hard_masked_method_call_examples(
        tmp_path, candidate_count=4
    ) == []


def test_binding_kind_and_invocation_shape_control_distractors(tmp_path):
    _write(tmp_path, """
class Factory:
    @classmethod
    def parse(cls, x):
        return int(x)

    @classmethod
    def decode(cls, x):
        return x

    @staticmethod
    def static_a(x):
        return x

    @staticmethod
    def static_b(x):
        return x

    @classmethod
    def caller(cls, x):
        return cls.parse(x)
""")
    examples = repository_hard_masked_method_call_examples(
        tmp_path, candidate_count=2, seed=0
    )
    assert len(examples) == 1
    names = {c.split("(", 1)[0] for c in examples[0].candidates}
    assert names == {"parse", "decode"}


def test_custom_instance_receiver_is_resolved(tmp_path):
    _write(tmp_path, """
class Pipeline:
    def normalize(this, x):
        return x.strip()

    def parse(this, x):
        return int(x)

    def clamp(this, x):
        return max(0, x)

    def emit(this, x):
        return str(x)

    def caller(this, x):
        return this.normalize(x)
""")
    examples = repository_hard_masked_method_call_examples(
        tmp_path, candidate_count=4, seed=3
    )
    assert len(examples) == 1
    assert "__CALL_TARGET__" in examples[0].context


def test_method_candidate_order_is_seeded(tmp_path):
    _write(tmp_path)
    a = repository_hard_masked_method_call_examples(tmp_path, candidate_count=4, seed=1)
    b = repository_hard_masked_method_call_examples(tmp_path, candidate_count=4, seed=1)
    c = repository_hard_masked_method_call_examples(tmp_path, candidate_count=4, seed=2)
    assert a == b
    assert any(x.candidates != y.candidates for x, y in zip(a, c))
