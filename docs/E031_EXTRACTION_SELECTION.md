# E031 — Preregistered extraction selection

This note records the extraction-only eligibility stage defined in
[E031_INDEPENDENT_REPLICATION_PREREG.md](E031_INDEPENDENT_REPLICATION_PREREG.md).

No encoder scoring, scorer training, generator inference, or end-to-end outcome
was observed on these repositories before this selection was fixed.

## Provenance

- workflow: `e031-extraction-census`
- run: `35789451409`
- analysis branch head: `5bac0516b5d2c2df8f3d0d2417067e86bc8c0663`
- aggregate artifact: `e031-extraction-selection`
- aggregate artifact digest:
  `sha256:83c58027dc70c1baad7902506d0ac76445977e541fa4af9515cb1373fdae8c84`

The workflow cloned every repository at its preregistered SHA and ran only the
frozen E027 function/method extractors with candidate count 4, body limit 512,
and seed 0.

## Census

Eligibility required at least 25 total examples across the two frozen task
families and at least 5 distinct source files.

| Order | Repository | Function | Method | Total | Source files | Eligible |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | google-deepmind/alphafold | 23 | 3 | 26 | 11 | yes |
| 2 | pyodide/pyodide | 34 | 19 | 53 | 16 | yes |
| 3 | optuna/optuna | 79 | 55 | 134 | 34 | yes |
| 4 | pytest-dev/pytest | 86 | 122 | 208 | 47 | yes |
| 5 | google/yapf | 19 | 59 | 78 | 15 | yes |
| 6 | DLR-RM/stable-baselines3 | 25 | 24 | 49 | 17 | yes |
| 7 | redis/redis-py | 99 | 239 | 338 | 61 | yes |
| 8 | getpelican/pelican | 7 | 22 | 29 | 9 | yes |

All eight candidates satisfy the eligibility rule.

## Selected replication set

The preregistration requires the **first four eligible repositories in frozen
pool order**, therefore E031 is now fixed to:

1. `google-deepmind/alphafold@c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. `pyodide/pyodide@e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. `optuna/optuna@7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. `pytest-dev/pytest@6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

Total primary tasks before leave-one-repository-out rotation: **421** across
**108 distinct source files**.

The remaining eligible repositories are not substitutes and must not be swapped
into the primary result based on model behavior.

## Next step

Run the preregistered E031 leave-one-repository-out experiment on exactly these
four repositories with the frozen E027 protocol.

The confirmatory gate remains:

- positive pooled assisted-minus-baseline success delta;
- exact two-sided McNemar p < 0.05;
- repository-stratified source-file bootstrap 95% lower bound > 0.

E029 rejection memory and E030 cross-file supervision remain excluded.
