# E038 — SmolLM2 ranked-correction transfer preregistration

E035 independently replicated the E032 ranked post-rejection recommendation
mechanism with Qwen 0.5B. E037 then established that the underlying first-turn
structured-selection intervention transfers to
`HuggingFaceTB/SmolLM2-360M-Instruct`.

E038 asks the next generator-dependence question: after SmolLM2 actually follows
a wrong decision recommendation and that choice is deterministically rejected,
does appending the scorer's next feasible ranked recommendation improve the
single correction turn over rejection memory alone?

This document freezes the eligible task population, generator, scorer,
feasibility predicate, correction prompts, parser, primary endpoint, and
statistics before any E038 correction-turn output is generated.

## Frozen historical entry population

Use the preserved E037 aggregate from:

- workflow run: `35855513250`;
- live commit: `cb0fa59e60743c25b3c84bc34f9f688bc55b42b5`;
- artifact: `e037-aggregate`;
- artifact id: `10749970897`;
- artifact digest:
  `sha256:0789ae4ca0263ee4aa82f488c281121a92733bd488b7dee7475bb657bb870c39`.

A task is eligible for E038 only if its preserved E037 first assisted turn
satisfies both conditions:

1. the frozen scorer recommendation was wrong
   (`recommendation_correct == false`);
2. SmolLM2's parsed first choice exactly equalled that wrong recommendation.

This selects tasks where the generator actually followed the decision evidence
and the deterministic verifier therefore rejected that recommended candidate.

Do **not** use the E037 second-turn result when selecting tasks or constructing
either E038 arm.

The expected frozen eligible population is:

| Repository | Eligible tasks | Source files |
| --- | ---: | ---: |
| AlphaFold | 6 | 4 |
| Pyodide | 9 | 7 |
| Optuna | 20 | 11 |
| pytest | 42 | 23 |
| **Total** | **77** | **45** |

Task-family counts:

| Family | Eligible tasks |
| --- | ---: |
| Functions | 38 |
| Methods | 39 |
| **Total** | **77** |

Any drift from these counts invalidates the run.

This population is intentionally conditioned on already-observed E037
first-turn behavior. E038 is therefore a preregistered **conditional
correction-mechanism transfer test**, not a fresh 421-task end-to-end replication.

## Frozen repository set and extraction

Use the exact E031/E037 repositories and revisions:

1. AlphaFold — `c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. Pyodide — `e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. Optuna — `7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. pytest — `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

Use the frozen same-file function and same-class method extractors:

- candidate count 4;
- candidate body characters 512;
- extractor seed 0.

The full extraction must still reproduce 421 tasks with the E031/E037 per-repo
counts before the 77-task historical entry filter is applied.

## Frozen decision scorer

Use the exact E031/E035/E037 scorer protocol:

- encoder: `nomic-ai/CodeRankEmbed`;
- `CodeRankEncoder(max_length=512, normalize_embeddings=False)`;
- `PairwiseMLPScorer(hidden=32)`;
- context focus radius 0;
- scorer seed 2;
- one training epoch;
- AdamW, lr `1e-3`, weight decay `1e-2`;
- training order seed 20001;
- batch size 32;
- gradient clip 1.0;
- leave-one-repository-out training.

Before any E038 correction result is accepted, reproduce the preserved E031/E037
top-1 counts:

| Held-out repository | Tasks | Top-1 correct | Top-1 wrong |
| --- | ---: | ---: | ---: |
| AlphaFold | 26 | 11 | 15 |
| Pyodide | 53 | 36 | 17 |
| Optuna | 134 | 87 | 47 |
| pytest | 208 | 110 | 98 |
| **Total** | **421** | **244** | **177** |

For each held-out repository, align the newly extracted/scored tasks with the
preserved E037 records in deterministic extraction order and require exact
row-wise identity of:

- repository;
- source path;
- function/method task family;
- answer index;
- top-1 recommendation index.

This order-aware guard is required because multiple distinct extracted tasks in
one source can legitimately share the same compact identity fields.

## Frozen generator

Use the exact E037 generator:

- model: `HuggingFaceTB/SmolLM2-360M-Instruct`;
- revision: `cbcad7f4d160a10174f725b968ab6faf2a76399e`;
- greedy decoding;
- `max_new_tokens=8`;
- model-native chat template;
- system message:
  `You are a precise code decision engine. Answer only with the requested candidate digit.`

Use the exact E037/E035 structured-index parser:

`^(?:candidate\\s*)?([1-4])(?:[.)]?)$`

case-insensitively after stripping surrounding whitespace.

No parser relaxation is allowed after outcomes are inspected.

## Hard feasibility

Use the frozen E024 `CallSiteBindable` predicate exactly as in E035.

The machine-labelled target must remain feasible on every eligible task. Any
soundness failure invalidates the run.

The preserved wrong first recommendation is the rejected candidate. Select the
next recommendation from the frozen scorer ranking after excluding that
candidate and any candidate rejected by the E024 feasibility mask.

## Paired correction arms

Generate exactly one new correction turn in each arm for each of the 77 eligible
tasks. The historical E037 first turn is not regenerated.

The rejected first candidate is removed from the visible candidate set in both
arms.

### Control — E029 rejection memory

Use the exact final E035 control correction prompt:

1. `Choose the one candidate that should replace __CALL_TARGET__.`
2. `Return only one digit from: <remaining candidate numbers>. Do not return code or explanation.`
3. caller;
4. remaining candidate blocks;
5. `That candidate violates the repository constraint. Choose another candidate number.`
6. `Candidate <rejected> was rejected by the deterministic verifier and is no longer eligible.`

No recommendation evidence is appended.

### Intervention — E032/E035 ranked correction

The control prompt above must be a byte-for-byte prefix.

Append exactly:

`Repository decision evidence (fallible): candidate <next feasible> is recommended.`

where `<next feasible>` is the highest-ranked candidate that:

- is not the preserved rejected first recommendation; and
- passes the frozen E024 feasibility mask.

No other wording change is allowed.

## Primary endpoint

Primary endpoint: exact correction success on the 77 eligible tasks.

Report:

- E029-memory correction successes;
- ranked-correction successes;
- paired both / ranked-only / memory-only / neither;
- paired correction-success delta;
- exact two-sided McNemar p;
- repository-stratified source-file-clustered bootstrap 95% CI for the paired
  correction-success delta.

Bootstrap:

- 5,000 replicates;
- resample source files within held-out-repository strata;
- RNG seed 38038.

The E038 transfer gate passes only if all three conditions hold:

1. ranked correction success > rejection-memory correction success;
2. exact two-sided McNemar p < 0.05;
3. clustered bootstrap 95% CI lower bound > 0.

No rescue criterion will be added after outcomes are seen.

## Secondary diagnostics

Report without changing the primary gate:

- next-feasible recommendation correctness;
- ranked-arm recommendation-following rate;
- parse-valid correction rate by arm;
- invalid-format counts by arm;
- per-repository paired results;
- function versus method paired results.

Because SmolLM2 did not deterministically follow first-turn recommendations in
E037, do not reconstruct the E035-style `244 + correction successes` overall
421-task success metric as though the first-turn process were identical. E038's
primary claim is conditional on an observed wrong recommendation being followed
and rejected.

## Interpretation

If E038 passes, ranked post-rejection evidence has transferred to a second
compact generator family on the subset where that generator actually entered
the intended rejected-recommendation state.

If E038 fails, preserve the result and treat the E032/E035 correction mechanism
as generator-dependent. Do not tune SmolLM2 prompts, parser permissiveness,
feasibility rules, scorer settings, or task selection on these 77 tasks and
rerun.

E038 does not alter E037's positive second-generator replication result.

## Stop rules

Do not:

- regenerate or reselect the E037 first-turn entry population;
- use E037 second-turn outcomes in task eligibility;
- change the 77-task eligibility rule after seeing E038 outputs;
- modify the E035 control or ranked correction wording;
- increase the correction-turn budget;
- change the scorer or E024 predicate;
- loosen the parser;
- prompt-tune SmolLM2 on these tasks after the result.
