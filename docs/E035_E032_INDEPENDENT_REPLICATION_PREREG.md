# E035 — Independent replication of E032 ranked correction

This document preregisters the development-independent replication of the final
E032 ranked re-recommendation intervention **before any E035 generator outcome
is inspected**.

E032 was finalized on the four development repositories after a prompt-order
ambiguity was discovered there. Its live result was therefore exploratory. E035
asks whether the exact final correction mechanism survives on the already frozen
E031 independent repository set.

## Primary question

After the frozen decision scorer makes a wrong first recommendation and that
candidate is deterministically rejected, does appending the scorer's next
feasible ranked recommendation improve second-turn recovery over E029-style
rejection memory alone?

## Frozen repository set

Use the exact E031 repositories and revisions:

1. AlphaFold — `c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. Pyodide — `e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. Optuna — `7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. pytest — `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

Use the exact E031 same-file function and same-class method extractors:

- candidate count 4;
- candidate body length 512;
- extractor seed 0.

Expected extraction counts are frozen:

| Repository | Functions | Methods | Total |
| --- | ---: | ---: | ---: |
| AlphaFold | 23 | 3 | 26 |
| Pyodide | 34 | 19 | 53 |
| Optuna | 79 | 55 | 134 |
| pytest | 86 | 122 | 208 |
| **Total** | 222 | 199 | **421** |

Any extraction drift invalidates the run.

## Frozen scorer

Use the exact E031/E027 scorer protocol:

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
- leave-one-repository-out training exactly as E031.

The scorer must reproduce the preserved E031 top-1 counts before any correction
outcome is accepted:

| Held-out repository | Tasks | Top-1 correct | Top-1 wrong |
| --- | ---: | ---: | ---: |
| AlphaFold | 26 | 11 | 15 |
| Pyodide | 53 | 36 | 17 |
| Optuna | 134 | 87 | 47 |
| pytest | 208 | 110 | 98 |
| **Total** | **421** | **244** | **177** |

These counts are derived from the preserved E031 aggregate artifact, not from
E035 outcomes.

## Frozen generator

Use the exact structured-index generator from E031/E032:

- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`;
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`;
- greedy decoding;
- `max_new_tokens=8`;
- parser:
  `^(?:candidate\\s*)?([1-4])(?:[.)]?)$` (case-insensitive);
- system prompt:
  `You are a precise code decision engine. Answer only with the requested candidate digit.`

## First-turn reproduction guard

For every one of the 177 tasks whose frozen scorer top-1 is wrong, rerun the
exact E031/E032 first-turn prompt with that top-1 recommendation.

The generated first choice must equal the scorer recommendation on every task.
Any mismatch invalidates the fold rather than being interpreted as an E032
effect.

The preserved E031 raw artifact recorded recommendation following on 421/421
first turns, so this guard checks deterministic reproduction under the frozen
model/revision/prompt.

## Hard feasibility

Use the existing E024 `CallSiteBindable` predicate exactly as in the final E032
development run.

The machine-labelled target must always remain allowed. A soundness failure
invalidates the run.

Turn zero remains the raw scorer top-1; E024 does **not** replace the first
recommendation in this replication. Its mask is used only when selecting the
next feasible recommendation after rejection, matching the final E032 live
protocol.

## Correction arms

Run only on the 177 wrong-first-recommendation tasks.

The rejected candidate is removed from the visible candidate set in both arms.

### Control — E029 rejection memory

The exact correction prompt is:

1. `Choose the one candidate that should replace __CALL_TARGET__.`
2. `Return only one digit from: <remaining candidate numbers>. Do not return code or explanation.`
3. caller;
4. remaining candidate blocks;
5. `That candidate violates the repository constraint. Choose another candidate number.`
6. `Candidate <rejected> was rejected by the deterministic verifier and is no longer eligible.`

No recommendation evidence is appended.

### Intervention — final E032 ranked correction

The control prompt above must be a byte-for-byte prefix.

Append exactly one final block:

`Repository decision evidence (fallible): candidate <next feasible> is recommended.`

where `<next feasible>` is the highest-ranked candidate that:

- is not the rejected first recommendation; and
- passes the frozen E024 feasibility mask.

No other wording changes are allowed.

## Outcomes

Primary unit: the 177 wrong-first-recommendation tasks.

Report:

- E029-memory correction successes;
- E032-ranked correction successes;
- paired both / E032-only / E029-only / neither;
- exact two-sided McNemar p;
- repository-stratified source-file-clustered bootstrap 95% CI for the paired
  correction-success delta;
- next-feasible recommendation correctness;
- generator recommendation-following on the correction turn;
- reconstructed overall two-attempt successes:
  `244 + correction successes` out of 421.

Also report by held-out repository and by function/method family.

## Primary replication gate

E035 passes only if all three conditions hold:

1. pooled E032-ranked correction success is greater than E029-memory correction
   success on the 177 wrong-first-recommendation tasks;
2. exact two-sided McNemar p < 0.05;
3. the 95% repository-stratified source-file-clustered bootstrap lower bound for
   the correction-success delta is > 0.

No rescue criterion will be added after outcomes are seen.

## Interpretation

If E035 passes, the post-rejection ranked-evidence mechanism has replicated on
the independent E031 repository population and can be treated as stronger than
development-set exploratory evidence.

If E035 fails, preserve the result and stop treating E032 ranked
re-recommendation as a general correction mechanism. Do not tune the prompt,
scorer, parser, feasibility predicate, or attempt budget on the E031
repositories.

## Separation from other work

E035 does not alter the E031 confirmatory result. It reuses the E031 repository
population only as a frozen independent test set for the already-finalized E032
mechanism.

E033/E034 generation-surface results are unrelated and remain stopped for the
pinned Qwen 0.5B generator.
