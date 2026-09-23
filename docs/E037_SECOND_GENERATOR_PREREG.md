# E037 — Second-generator replication preregistration

E031 independently replicated the structured-selection intervention with
Qwen/Qwen2.5-Coder-0.5B-Instruct. E037 asks whether that end-to-end effect
depends on that generator.

This preregistration freezes the second generator, repository set, decision
scorer, prompt/parser, attempt budget, primary endpoint, and statistics before
any E037 generator outcome is inspected.

## Generator

Use:

- model: `HuggingFaceTB/SmolLM2-360M-Instruct`;
- revision: `cbcad7f4d160a10174f725b968ab6faf2a76399e`;
- greedy decoding;
- `max_new_tokens=8`;
- model-native chat template;
- same system message as E031:
  `You are a precise code decision engine. Answer only with the requested candidate digit.`

The user prompt, candidate numbering, deterministic feedback, and parser are
identical to E031. Only the generator family changes.

The revision is pinned before any task outcome is generated.

## Repository set

Use the exact E031 independent repositories and revisions:

1. AlphaFold — `c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. Pyodide — `e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. Optuna — `7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. pytest — `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

Use the frozen E031 extractors:

- candidate count 4;
- candidate body characters 512;
- seed 0;
- same-file function and same-class method tasks only.

Expected counts:

| Repository | Functions | Methods | Total |
| --- | ---: | ---: | ---: |
| AlphaFold | 23 | 3 | 26 |
| Pyodide | 34 | 19 | 53 |
| Optuna | 79 | 55 | 134 |
| pytest | 86 | 122 | 208 |
| **Total** | **222** | **199** | **421** |

Any extraction drift invalidates the run.

## Frozen decision model

Use the exact E031 scorer protocol:

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

The scorer must reproduce the preserved E031 top-1 counts before generator
outcomes are accepted:

| Held-out repository | Tasks | Top-1 correct |
| --- | ---: | ---: |
| AlphaFold | 26 | 11 |
| Pyodide | 53 | 36 |
| Optuna | 134 | 87 |
| pytest | 208 | 110 |
| **Total** | **421** | **244** |

The decision layer is therefore held fixed while generator family changes.

## Structured-selection protocol

Use the exact E031 live protocol:

### Baseline arm

Prompt contains:

1. the frozen instruction;
2. caller;
3. all four candidates;
4. deterministic verifier feedback after a failed first attempt.

No decision recommendation is shown.

### Assisted arm

The same prompt, plus:

`Repository decision evidence (fallible): candidate <n> is recommended.`

The same recommendation remains present on the correction turn, matching E031.

### Parser

Accept only:

`^(?:candidate\\s*)?([1-4])(?:[.)]?)$`

case-insensitively after stripping surrounding whitespace.

### Verification and budget

- deterministic exact candidate verifier;
- maximum two attempts per arm;
- same category-only feedback as E031;
- no prompt tuning or parser relaxation after outcomes are seen.

## Primary endpoint

Primary endpoint: success within two attempts.

Report:

- baseline successes / 421;
- assisted successes / 421;
- paired assisted-minus-baseline success-rate delta.

The preregistered replication gate passes only if all three conditions hold:

1. assisted success > baseline success;
2. exact two-sided McNemar p < 0.05;
3. repository-stratified source-file-clustered bootstrap 95% CI lower bound > 0.

Bootstrap:

- 5,000 replicates;
- resample source files within held-out-repository strata;
- RNG seed 27027.

If any condition fails, record E037 as not replicating the E031 effect with this
generator. Do not tune SmolLM2 on the E031 repositories and rerun.

## Secondary diagnostics

Report, without changing the primary gate:

- first-pass success by arm;
- parse-valid response rate by arm and attempt;
- terminal failures;
- mean attempts within the two-attempt budget;
- assisted first-turn recommendation-following rate;
- per-repository results;
- function versus method results.

These diagnostics explain generator dependence but cannot rescue a failed
primary endpoint.

## Ranked correction is out of scope

E035 independently replicated the E032 ranked re-recommendation mechanism for
Qwen 0.5B.

E037 does **not** test that mechanism. Mixing it into the second-generator test
would make it unclear whether a result comes from first-turn assistance or from
post-rejection ranking.

If E037 establishes a usable structured-selection regime for SmolLM2, a
separate E038 may preregister ranked-correction transfer without changing the
E037 result.

## Stop rules

Do not:

- alter the E031 prompt for SmolLM2;
- change parser permissiveness;
- increase the attempt budget;
- swap repository tasks;
- change the scorer;
- retune on E031 after the result;
- interpret invalid output as a deterministic repair.

A null or negative result is informative generator-dependence evidence and must
be preserved as such.
