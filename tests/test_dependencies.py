from pathlib import Path


def test_unixcoder_optional_dependency_stays_on_transformers_4():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'hf = ["transformers>=4.45,<5"]' in text
