#!/usr/bin/env python3
"""E022 smoke: optional HF generator on a single repair example.

Does not run in default CI. Requires:

    pip install -e ".[hf]"

and a network fetch of the pinned model on first use.

    python examples/run_corrective_turn_hf_smoke.py
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        from cdm.hf_generator import make_hf_generator_factory
        from cdm.repair import run_paired_repair
        from cdm.synthetic import DecisionExample
    except ImportError as exc:
        print("import failed:", exc, file=sys.stderr)
        return 1

    example = DecisionExample(
        context="""def caller(value):
    prepared = value.strip()
    return __CALL_TARGET__(prepared)
""",
        question="Which candidate definition should replace __CALL_TARGET__?",
        candidates=(
            """normalize(value)
def normalize(value):
    return value.lower()
""",
            """parse(value)
def parse(value):
    return int(value)
""",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="smoke::example.py",
    )

    try:
        factory = make_hf_generator_factory(
            model_name="Salesforce/codegen-350M-mono",
            max_new_tokens=128,
            temperature=0.0,
            seed=0,
        )
        # Probe that the optional stack loads before running both arms.
        _ = factory()
    except ImportError as exc:
        print("hf extra not installed:", exc)
        print("install with: pip install -e '.[hf]'")
        return 2
    except Exception as exc:  # noqa: BLE001 — smoke path reports any load error
        print("model load failed:", type(exc).__name__, exc)
        return 3

    paired = run_paired_repair(
        example,
        factory,
        recommendation_index=example.answer_index,
        max_attempts=2,
    )
    print(
        "baseline",
        paired.baseline.success,
        paired.baseline.attempts_used,
        paired.baseline.correction_turns,
    )
    print(
        "assisted",
        paired.assisted.success,
        paired.assisted.attempts_used,
        paired.assisted.correction_turns,
    )
    print("success_delta", paired.success_delta)
    print("correction_turn_delta", paired.correction_turn_delta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
