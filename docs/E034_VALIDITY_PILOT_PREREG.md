# E034 — Baseline validity pilot preregistration

This pilot is registered before inspecting any Qwen outputs on E034.

## Question

Can the frozen compact generator reliably emit the closed-vocabulary E034 plan
format without decision-model assistance?

E034 is not allowed to proceed to a paired baseline-vs-assisted experiment
unless the generator first crosses a useful validity floor on this baseline-only
pilot.

## Frozen generator

- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
- greedy decoding
- one generation per task
- `max_new_tokens=32`
- no scorer recommendation
- no corrective turn

## Repository set

Use the exact four E027 development repositories and pinned revisions:

1. browser-use — `d8110c5ff87ccba887aaa726cdb780f2f84bef8d`
2. crawl4ai — `862f6bccb9c063f49b9d42701baa0eea17a4993f`
3. markitdown — `b8f79c57ebc0044be41323d89b2a45d3fda8460e`
4. scrapling — `08f107b1240fd72847b0f5e10426c7e6cc16e67e`

Extract the existing same-file function, same-class method, and E030 cross-file
families with candidate count 4, candidate body length 512, and extractor seed
0.

For each base decision, construct E034 with `argument_repair_example(seed=0)`.
Only default semantic perturbations are eligible. Every selected base example
must pass `corruption_is_label_invariant()`.

## Outcome-blind sample

Target: 64 E034 tasks.

Selection must be independent of the hidden answer label. The stable sampling
key contains repository, family, source identifier, task identifier, caller
context, and candidate strings, but **not** `answer_index`, restoring plan,
verifier result, or model output.

Start with a quota of four tasks per repository × family stratum where available,
then fill any deficit from the remaining eligible tasks in global stable-hash
order.

No model outcome may affect inclusion.

## Primary characterization funnel

Report counts and rates for:

1. plan syntax valid under `parse_operation_plan`;
2. all identifier operands inside `plan_vocabulary`;
3. operation applicable at the visible call site;
4. edited call bindable to the selected candidate;
5. selected candidate equals the hidden target;
6. selected operation equals the hidden restoring operation;
7. exact deterministic repair success.

Also report verifier-reason distribution, generation time, and the same funnel by
repository, task family, and perturbation type.

## Deterministic baselines

For every sampled task, compute before model inference:

- `predicate_census.solved_by_predicate`;
- `predicate_census.pure_selection`;
- plan-space size;
- number of binding plans;
- number of surviving candidates.

The model's exact success must be compared with the predicate-alone count. Pure
selection is descriptive: it identifies tasks where bindability reduces E034 to
one plan per candidate.

## Interpretation rule

This is a characterization pilot, not a confirmatory hypothesis test. There is
no post-hoc significance threshold.

Proceed to a paired E034 baseline-vs-assisted experiment only if all of the
following qualitative conditions hold:

- syntax/vocabulary validity is substantially above E033's free-form 56.3%
  parse-valid rate;
- most syntactically valid outputs survive applicability and bindability rather
  than failing because the generator cannot operate the schema;
- exact restoration materially exceeds the deterministic predicate-alone
  baseline;
- failures are concentrated in target/operation choice rather than format
  collapse.

If the closed schema still produces low parse/applicability/bindability validity,
stop this surface for the pinned 0.5B generator. Do not rescue it by silently
repairing plans, expanding the parser, or tuning on the 64 pilot tasks.

## Separation from frozen results

This pilot does not alter E027, E031, or the E032 independent-replication gate.
It uses the development repositories only to characterize the new generation
surface.
