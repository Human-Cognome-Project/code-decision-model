# Open exploratory directions

E031 has now passed the preregistered development-independent replication gate. This document therefore tracks work **after** independent replication rather than treating it as still pending.

## Completed foundations

### E031 — independent replication

The frozen E027 intervention replicated on 421 tasks from AlphaFold, Pyodide, Optuna, and pytest:

- baseline success: 200/421 (47.5%);
- assisted success: 287/421 (68.2%);
- paired delta: +20.67 pp;
- exact McNemar p = 1.29e-11;
- repository-stratified source-file bootstrap 95% CI: +13.97 to +27.46 pp.

This closes the main development-leakage concern left by E027. Do not retune this result.

### E028/E029 — failure mechanism and rejection memory

E028 showed that first-turn recommendation following is effectively deterministic under the frozen index protocol and that remaining assisted failures begin with wrong recommendations.

E029 then removed verifier-rejected candidates from the correction turn. It nearly eliminated immediate repetition of the rejected choice but did not materially improve final success: 289/400 -> 292/400, clustered 95% CI -0.96 to +2.32 pp.

Do not spend cycles prompt-tuning E029 on the development repositories.

## E032 ranked feasible re-recommendation — development-set result complete

The final live intervention preserves the E029 correction prompt exactly and
appends the historical recommendation sentence for the scorer's next feasible
candidate.

Result:

- E029: 292/400 (73.0%) success within two attempts;
- E032: 315/400 (78.75%);
- wrong-first-recommendation recovery: 56/164 (34.1%) -> 79/164 (48.2%);
- wrong-subset delta: +14.02 pp;
- exact McNemar p = 0.0128;
- source-file-clustered bootstrap 95% CI: +2.07 to +25.49 pp;
- second recommendation followed on 156/164 correction turns.

This is useful exploratory evidence but it was finalized on the development
repositories after a prompt-order ambiguity was discovered there.

### Next E032 gate

Freeze the exact final prompt and replicate the ranked-correction mechanism on
the E031 independent repository set.

Do not change:

- scorer recipe;
- first-turn prompt;
- E029 correction prefix;
- appended recommendation wording;
- parser;
- two-attempt budget;
- statistics.

A failure to reproduce the correction benefit on the E031 repositories should
stop treating ranked re-recommendation as a general mechanism.

## E033 — call-expression intent (stopped at validity gate)

The baseline-only 64-task validity pilot produced:

- 36/64 parse-valid call expressions (56.3%);
- 23/64 uniquely resolved and bindable calls (35.9%);
- 2/64 exact repairs (3.1%).

The failures were mostly bare symbols, partial signatures, retained placeholders,
wrong targets, or wrong arguments. A permissive deterministic parser that
reconstructed omitted calls or arguments would collapse the task back toward
index selection and would not be a valid rescue.

Do not proceed to a full paired E033 run with this generator/prompt surface.

A successor should constrain the action space structurally rather than rely on
free-form call text. Useful possibilities include a narrow AST-operation schema
that separates target choice from explicit argument operations.

## Second-generator replication

Now that E031 is complete, repeat the **frozen E031 intervention** with another compact open generator.

The purpose is not to improve Qwen's result. It is to measure generator dependence.

Freeze:

- repository set and revisions;
- decision scorer recipe;
- structured index protocol;
- parser;
- attempt budget;
- deterministic statistics.

A second generator may use GPU for practical throughput, but hardware must not change the decoding semantics.

## Harder deterministic decision types

E030 establishes one cross-file task. Further useful targets include:

- LSP symbol/reference resolution;
- compiler/type-checker diagnostic resolution;
- import/module selection;
- deterministic API compatibility;
- mutation/test outcomes.

A task needs a deterministic verifier before model work begins.

## Repository-scale retrieval

Test a two-stage path:

1. independent/cacheable retrieval or shortlisting;
2. decision-model reranking.

Measure separately:

- target recall after retrieval;
- reranking accuracy;
- end-to-end corrective burden.

Do not hide retrieval misses inside decision accuracy.

## Confidence and escalation

E020 falsified raw Potion cosine margin as a useful general routing signal.

More useful options include:

- calibrated decision-head confidence on unseen repositories;
- agreement between independent hard constraints and neural ranking;
- abstention evaluated without tuning on E027/E031 test repositories.

## Leaner decision path

Explore smaller/cheaper representations only against a frozen end-to-end effect:

- smaller encoders;
- quantized/static embeddings;
- lower-dimensional projections;
- simpler heads;
- cached repository representations.

A cheaper path is useful only if corrective-burden performance survives.

## Lower-value directions

Avoid:

- larger heads without an end-to-end reason;
- more tuning on E027 repositories;
- retuning E031 after the confirmatory result;
- further prompt tuning of E029;
- raw Potion-margin routing;
- general agent loops;
- soft preferences or LLM-generated supervision where deterministic labels exist;
- free-form patch generation without deterministic verification.

## Contribution rule

An exploratory PR should state:

1. the open question;
2. the deterministic success/failure signal;
3. the comparison baseline;
4. the outcome that would stop the direction.
