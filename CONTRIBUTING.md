# Contributing

Thank you for considering a contribution. This project is intentionally narrow and disciplined. Contributions that preserve that discipline are welcome.

## Before you start

- Read `docs/ARCHITECTURE.md`.
- Skim the existing experiment notes in `docs/E0xx_*.md`.
- Read `AGENT.md` (applies to both human and automated contributors).

## Design constraints you must respect

- Context, question, and candidates are encoded **independently**.
- Prefer machine-verifiable (deterministic) supervision.
- Keep the decision head lean.
- Do not introduce external theoretical framing or soft predicates.
- The practical goal remains reduction in corrective turns when paired with a small generator.

## Development setup

```bash
python -m pip install -e ".[dev]"
pytest
```

Optional extras exist for specific encoders (`hf`, `coderank`). See `pyproject.toml`.

## Making a change

1. Create a focused branch.
2. Keep the diff small and purposeful.
3. Add or update tests.
4. If you add a new experiment or measurement, document it under `docs/` using the existing numbering and style.
5. Ensure CPU-only tests still pass without requiring model downloads for the core path.

## Pull requests

Use the PR template. In particular, state:

- Which experiment or success criterion the change advances.
- That independent encoding of context / question / candidates is preserved.
- Whether any new supervision is machine-verifiable.
- Whether the change moves toward (or away from) end-to-end corrective-turn measurement.

PRs that expand scope, add soft constraints, or increase complexity without a clear measurement benefit are likely to be declined.

## Code style

- Match the existing tone and structure.
- Prefer clarity and explicitness over cleverness.
- Avoid unnecessary abstractions.

## Questions

Open an issue using one of the templates if you want to discuss a direction before implementing.
