from pathlib import Path

from cdm.repository import (
    collect_python_symbols,
    repository_call_examples,
    split_repository_examples,
    write_jsonl_dataset,
)


def _write_repo(root: Path) -> None:
    (root / "pkg").mkdir()
    (root / "pkg" / "alpha.py").write_text(
        """
def normalize(x):
    return x.strip()

def parse(x):
    return int(x)

def stage_one(x):
    return normalize(x)

def stage_two(x):
    return parse(x)
""",
        encoding="utf-8",
    )
    (root / "pkg" / "beta.py").write_text(
        """
def clamp(x):
    return max(0, x)

def emit(x):
    return str(x)

def stage_three(x):
    return clamp(x)

def stage_four(x):
    return emit(x)
""",
        encoding="utf-8",
    )
    (root / "pkg" / "gamma.py").write_text(
        """
def encode(x):
    return bytes(str(x), "utf-8")

def store(x):
    return encode(x)
""",
        encoding="utf-8",
    )
    (root / ".venv").mkdir()
    (root / ".venv" / "ignored.py").write_text(
        "def hidden():\n    return 1\n",
        encoding="utf-8",
    )


def test_repository_examples_use_repository_wide_candidates_and_provenance(tmp_path):
    _write_repo(tmp_path)

    examples = repository_call_examples(
        tmp_path,
        max_candidates=6,
        seed=11,
    )

    assert len(examples) == 5
    assert all(example.task == "python.direct_call" for example in examples)
    assert all(example.source for example in examples)
    assert all(len(example.candidates) == 6 for example in examples)
    assert all(
        example.candidates[example.answer_index].startswith("pkg/")
        for example in examples
    )
    assert any(
        len({candidate.split("::", 1)[0] for candidate in example.candidates}) > 1
        for example in examples
    )


def test_candidate_order_is_deterministic_and_seeded(tmp_path):
    _write_repo(tmp_path)

    a = repository_call_examples(tmp_path, max_candidates=6, seed=7)
    b = repository_call_examples(tmp_path, max_candidates=6, seed=7)
    c = repository_call_examples(tmp_path, max_candidates=6, seed=8)

    assert a == b
    assert any(x.candidates != y.candidates for x, y in zip(a, c))


def test_file_level_splitting_prevents_source_leakage(tmp_path):
    _write_repo(tmp_path)
    examples = repository_call_examples(tmp_path, max_candidates=5, seed=3)

    dataset = split_repository_examples(
        examples,
        seed=9,
        train_fraction=0.5,
        validation_fraction=0.25,
    )

    sources = {
        "train": {e.source for e in dataset.train},
        "validation": {e.source for e in dataset.validation},
        "test": {e.source for e in dataset.test},
    }
    assert sources["train"].isdisjoint(sources["validation"])
    assert sources["train"].isdisjoint(sources["test"])
    assert sources["validation"].isdisjoint(sources["test"])
    assert set().union(*sources.values()) == {e.source for e in examples}


def test_jsonl_dataset_writer_and_excluded_dirs(tmp_path):
    _write_repo(tmp_path)
    symbols, by_file = collect_python_symbols(tmp_path)

    assert all(".venv" not in symbol.source for symbol in symbols)
    assert ".venv/ignored.py" not in by_file

    examples = repository_call_examples(tmp_path, max_candidates=4)
    dataset = split_repository_examples(
        examples,
        train_fraction=0.5,
        validation_fraction=0.25,
    )
    paths = write_jsonl_dataset(dataset, tmp_path / "dataset")

    assert set(paths) == {"train", "validation", "test"}
    assert all(path.exists() for path in paths.values())
