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

## E032/E035 — ranked feasible re-recommendation (independently replicated)

E032 finalized the ranked correction mechanism on the development repositories:
after deterministic rejection, append the scorer's next feasible ranked
recommendation to the unchanged E029 correction prompt.

Development result:

- E029 correction recovery: 56/164 (34.1%);
- E032 ranked recovery: 79/164 (48.2%);
- delta: +14.02 pp;
- exact McNemar p = 0.0128;
- clustered 95% CI: +2.07 to +25.49 pp.

E035 then preregistered the exact final intervention on the frozen E031
independent repositories. The replication passed all three preregistered gates:

- E029 correction recovery: 62/177 (35.0%);
- ranked correction recovery: 111/177 (62.7%);
- delta: +27.68 pp;
- exact McNemar p = 3.48e-7;
- clustered 95% CI: +17.65 to +37.16 pp;
- second recommendation followed on 164/177 correction turns.

Reconstructed overall success on the 421-task independent set was 306/421
(72.7%) under E029-style rejection memory versus 355/421 (84.3%) with ranked
re-recommendation.

Treat the post-rejection ranked-evidence mechanism as independently replicated
for the frozen Python structured-selection task. Do not retune E035 on the E031
repositories.

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

E034 tested that successor idea with a closed candidate-plus-one-operation
language. It also failed the generation-validity gate for Qwen 0.5B, so do not
continue narrowing schemas on this generator.

## E034 — closed-vocabulary argument operations (stopped at validity gate)

The preregistered baseline-only 64-task pilot produced:

- syntax-valid plans: 11/64 (17.2%);
- bindable edited calls: 2/64 (3.1%);
- correct target: 1/64 (1.6%);
- correct restoring operation: 0/64;
- exact repairs: 0/64.

All 64 model outputs anchored on candidate 1. Every parsed plan was exactly
`candidate 1; keep`. Of the 53 invalid outputs, 45 copied or began reproducing
candidate 1's signature/body instead of emitting a plan.

The deterministic predicate did not solve the sample by itself (0/64), although
29/64 tasks were pure-selection cases with exactly one binding plan per
candidate. The generator still failed to express the required operation.

This sharpens the current boundary for the pinned Qwen 0.5B model: candidate
selection is reliable; generated edit intent is not, even under a closed
single-operation vocabulary.

Do not:

- run a paired assisted E034 experiment with this generator;
- prompt-tune on the 64 pilot tasks;
- loosen or normalize the parser after seeing the outputs;
- create another narrower edit schema for Qwen 0.5B.

If structured edit intent is revisited, change the generator capability under a
fresh preregistration instead of changing the task around this result.

## E036 — canonical continuation likelihood (stopped)

E036 tested the exact E034 64-task sample by scoring every admitted plan using
the pinned Qwen model's canonical continuation likelihood under a frozen prompt
token boundary.

- uniform over E024-binding plans: 12.32/64 expected exact;
- unrotated summed likelihood: 0/64;
- four-way rotated summed likelihood: 10/64;
- unrotated candidate-1 top-plan frequency: 64/64;
- rotated mapped-back winner histogram: 13/13/18/20.

The rotated histogram is not evidence by itself that the position prior
cancelled: cross-candidate ties can still be assigned a nominal winner by the
tie-break or floating-point rounding. The live aggregate predates the explicit
`top_candidate_ties` diagnostic, so tie counts cannot be reconstructed from it.

Both primary summed-likelihood variants remained at or below the preregistered
predicate-plus-uniform floor, so the stop condition fired and no paired assisted
E036 run should occur.

Feasible-only summed ranking reached 16/64 unrotated and 19/64 rotated, but this
was a secondary diagnostic, not the continuation gate. Do not convert it into a
post-hoc pass criterion. E036 was not exact grammar-constrained decoding.

## E037 — second-generator replication (completed)

The frozen E031 structured-selection intervention was repeated with
`HuggingFaceTB/SmolLM2-360M-Instruct` at pinned revision
`cbcad7f4d160a10174f725b968ab6faf2a76399e`.

Result on the same 421 independent tasks:

- baseline success within two attempts: 113/421 (26.8%);
- assisted success: 160/421 (38.0%);
- paired delta: +11.16 pp;
- exact McNemar p = 2.05e-9;
- source-file-clustered 95% CI: +7.74 to +14.42 pp.

All three preregistered gates passed. The effect therefore transfers to a
second compact generator family, although SmolLM2 showed materially weaker
first-turn recommendation following (181/421, 43.0%) and lower assisted
first-turn parse validity (305/421, 72.4%) than the Qwen run.

E038 completed the next generator-dependence test; see below. Do not tune E037
on these 421 tasks.

## E038 — ranked correction transfer (completed)

E038 conditioned on the 77 E037 tasks where SmolLM2 actually followed a wrong
first recommendation and therefore entered the intended deterministic rejection
state.

- rejection-memory correction: 11/77 (14.3%);
- ranked correction: 28/77 (36.4%);
- delta: +22.08 pp;
- exact McNemar p = 0.00232;
- source-file-clustered 95% CI: +9.21 to +35.21 pp;
- next feasible recommendation correct: 55/77 (71.4%);
- ranked recommendation followed: 38/77 (49.4%).

All three preregistered transfer gates passed. This extends the E032/E035
post-rejection mechanism to a second compact generator family, conditional on
the generator actually entering the rejected-recommendation state.

Do not retune the SmolLM2 correction prompt, parser, eligibility filter, scorer,
or feasibility rule on these 77 tasks.

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

E040 measured the deterministic retrieval stage without a model: in-scope and
repository pools per task, E024 pruning, and pool-complete re-posed tasks.

E041 completed the first live pool-scale gate on the exact E031 same-file
function task. Over all 222 complete E024-bindable in-scope pools, the frozen
scorer achieved 82/222 top-1 versus 27.73 expected under predicate-plus-uniform
choice. Mean excess was +24.45 pp with clustered 95% CI +13.57 to +35.67 pp,
and all four repository folds were positive. Pool size averaged 11.43 candidates
with median 8 and maximum 42.

This passes direct full-scope reranking. E042 preregisters the repository-scale
gate on the same 222 tasks and frozen scorer, with exact E031 and E041 continuity
guards. Repository-pool outcomes are compared against per-task uniform choice
over the actual E024-bindable repository pool. No retrieval or generator stage
is introduced until that direct-ranking boundary is measured.

## Confidence and escalation

E020 falsified raw Potion cosine margin as a useful general routing signal.

E039 then tested the PairwiseMLP head's own raw top-class softmax probability.
An E027-fitted threshold of 0.35 routed 385/421 E031 tasks to assistance and
produced 289/421 successes versus 287/421 under always-assist. The +0.48 pp
delta was not significant (McNemar p = 0.774; clustered 95% CI -1.45 to +2.26
pp), so the preregistered gate failed.

Do not tune another top-softmax threshold or calibration transform on E031.
Future escalation work should use a meaningfully different preregistered signal,
for example agreement between independent hard constraints and neural ranking,
and should preserve a genuinely untouched evaluation population.

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
