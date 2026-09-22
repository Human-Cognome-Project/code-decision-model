# E031 — Development-independent replication result

E031 was preregistered before extraction density or model outcomes were inspected. The fixed primary repository set was AlphaFold, Pyodide, Optuna, and pytest, using the frozen E027 task, scorer, generator, parser, two-attempt budget, and E026 paired statistics.

## Provenance

- workflow: `e031-independent-replication`
- run: `35789900382`
- branch: `analysis/e031-independent-replication-live`
- head SHA: `f339aa4b276ae1b022c2b30d692105ee3db5c655`
- aggregate artifact: `e031-aggregate`
- artifact digest: `sha256:fe17974a3a1e1d75f20cb10343dc501f7dd2affd80946c2272cacbc5dacf2951`
- tasks: 421
- source files: 108

## Primary result

| Arm | Success within 2 attempts | First-pass success |
| --- | ---: | ---: |
| Baseline | 200/421 (47.5%) | 91/421 (21.6%) |
| Assisted | 287/421 (68.2%) | 244/421 (58.0%) |

Paired micro success-rate delta: **+20.67 percentage points**.

The preregistered source-file clustered bootstrap, stratified by held-out repository, gave a 95% interval of **+13.97 to +27.46 percentage points** for the success delta. Exact two-sided McNemar p was **1.29e-11**.

The preregistered confirmatory gate passed all three conditions:

- pooled assisted-minus-baseline success delta was positive;
- exact McNemar p was below 0.05;
- the clustered bootstrap lower bound was above zero.

## Corrective burden

Among the 159 tasks where both arms succeeded:

- assisted used fewer correction turns on 70;
- the arms tied on 89;
- assisted used more correction turns on 0.

Mean baseline-minus-assisted correction-turn delta among paired successes was **+0.440**. Exact two-sided sign p was **1.69e-21**.

Mean attempts across all tasks fell from **1.784** baseline to **1.420** assisted.

## Decision accuracy

The frozen decision scorer achieved:

- micro accuracy: **57.96%**;
- repository-macro accuracy: **57.01%**.

As in E027, assisted first-pass success equals decision accuracy because the generator follows the recommendation with very high fidelity under the structured index protocol.

## Repository results

| Held-out repository | Baseline success | Assisted success | Delta |
| --- | ---: | ---: | ---: |
| AlphaFold | 11/26 (42.3%) | 16/26 (61.5%) | +19.2 pp |
| Optuna | 63/134 (47.0%) | 99/134 (73.9%) | +26.9 pp |
| Pyodide | 33/53 (62.3%) | 41/53 (77.4%) | +15.1 pp |
| pytest | 93/208 (44.7%) | 131/208 (63.0%) | +18.3 pp |

Every repository fold was positive. The small AlphaFold fold remains descriptive on its own.

## Interpretation

E031 closes the principal development-leakage concern left by E027. The same frozen intervention produced a similar end-to-end gain on a second repository set that did not influence architecture, encoder choice, scorer shape, prompting, thresholds, or the replication pass criterion.

This does not establish universality across programming languages, generators, or repair types. It does establish that the E027 corrective-burden effect survives a preregistered development-independent Python repository replication.

Exploratory work after this result must remain clearly separated from the frozen E031 evidence.
