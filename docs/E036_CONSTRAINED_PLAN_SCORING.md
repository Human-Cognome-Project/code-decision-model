# E036 — Constrained plan scoring over the E034 plan space

E034's preregistered validity pilot failed for the pinned Qwen 0.5B generator:
11/64 outputs parsed as plans, all 11 were `candidate 1; keep`, 45/64 copied
candidate 1's signature or body, and exact restoration was 0/64. The recorded
conclusion is that, for this generator, "the demonstrated practical regime is
selection, not generated edit intent", and that a future structured-edit
experiment should change generator capability under a fresh preregistration
rather than change the task around the result.

E036 is that capability change, and it is the cheapest one available: the same
weights, the same prompt, the same task, and a different decoder. It does not
reopen E034's verdict. E034 measured whether the generator can *emit* a plan;
E036 measures whether it *knows* one.

## Mechanism

The E034 plan space is finite: `plan_space(item)` enumerates candidate ×
single operation over the closed vocabulary, typically 40 to 100 plans, and it
is exactly the set the E034 verifier admits past its first two gates. So the
generator does not have to produce text at all. For every plan it computes

```text
log P(render(plan) + <end-of-turn> | E034 prompt)
```

where `render(plan)` is tokenised on its own after the frozen prompt token
sequence, and the highest-scoring plan is the output. Call this **canonical
continuation likelihood ranking under a frozen prompt token boundary**. Format
validity is 100% by construction, so the E034 funnel collapses to two
questions:

1. Does the likelihood rank the restoring plan above chance over the plan
   space, and above the model-free predicate-plus-ranker baseline?
2. How much of the ranking is the candidate-1 position prior that E034
   exposed, as opposed to a preference for the right candidate and operation?

**What this measurement is not.** It is not exact grammar-constrained
decoding, and its top plan is not proven to be the maximum a posteriori plan
under a grammar constraint. A token-level constrained decoder may admit more
than one token sequence that decodes to the same plan; the plan's probability
under such a decoder is the sum over all admissible tokenisations, and its
argmax can differ from the argmax over one canonical tokenisation per plan.
E036 scores exactly one sequence per plan: the continuation string tokenised in
isolation, checked to decode back to the plan, followed by the end-of-turn id.
The round-trip check proves that sequence is valid, not that it is unique or
that it carries the plan's whole mass. A positive result therefore means that
canonical plan likelihood carries signal about the target and the operation;
it does not by itself prove that grammar-constrained decoding would fix E034's
emission failure. Exhaustive scoring over all admissible tokenisations is a
possible follow-up if the canonical result warrants it.

The corrective turn is deterministic, as in E032: a verifier-rejected plan is
removed and the next-ranked plan is tried. No re-prompting is involved, so a
paired run costs one scoring pass per arm per task.

The decision model is untouched. Its only role is the E027 recommendation
sentence in the assisted arm's prompt, exactly as in E034.

## Label-free controls

- **Length normalisation** (secondary ranking): the summed log-probability
  favours the shortest plan, and the shortest plan is always `keep`. The mean
  per-token log-probability is reported alongside, preregistered as secondary.
- **Cyclic candidate rotation**: the prompt is re-rendered with the candidates
  rotated (`cyclic_orders`), each plan is scored under every rotation with its
  index mapped to the shown position, and scores are averaged after mapping
  back. A preference for a candidate *position* cancels; a preference for a
  candidate's *content* survives. Rotation depends only on the candidate count,
  never on the label, so the set of prompts is a function of visible content.
  `top_candidate_histogram` reports how often each shown position wins; E034's
  free generation gave (64, 0, 0, 0).
- **Feasible-only ranking** (`feasible_only=True`): restrict the ranked space
  to plans that already bind their candidate (E024). This is the deterministic
  layer acting before the generator rather than after; reported separately
  because it changes what the generator is asked to rank.

## Model-free baselines (per task, analytic)

`chance_baselines(item, recommendation_index=...)` gives the expected exact
first-pass success of choosers that use no generator:

| Chooser | Expected success |
| --- | --- |
| uniform over the plan space | 1 / plan space size |
| uniform over binding plans | 1 / binding plans, or 0 if the restoring plan does not bind |
| uniform over binding plans of the recommended candidate | 1 / that count if the recommendation is correct, else 0 |
| E034 attractor `candidate 1; keep` | 0, since a restoring operation is never `keep` |

On this repository's 121 E034 tasks (mock script, correct recommendation given):

| Chooser | Expected exact |
| --- | ---: |
| uniform over plan space | 3.1 / 121 |
| uniform over binding plans | 26.3 / 121 |
| binding plans of a correct recommendation | 81.9 / 121 |
| `candidate 1; keep` | 0 / 121 |

The third row is the bar that matters: with a correct recommendation, the
predicate alone already leaves the right plan a 1-in-1 or 1-in-few choice on
most tasks. A generator adds value only if its likelihood beats that, or
recovers cases where the recommendation is wrong. A live result must be
reported against this row, not against uniform chance.

## Implementation

`src/cdm/plan_scoring.py`:

- `PlanScorer`: `(prompt, continuations) -> [ContinuationScore]`, deterministic,
  reading nothing but the strings.
- `rank_plans(item, scorer, *, recommendation_index, candidates, shifts,
  normalize)`: every plan, best first; ties break by plan-space order, so a
  constant scorer reproduces the E034 attractor exactly.
- `run_plan_scoring_loop` / `run_paired_plan_scoring`: the deterministic
  corrective loop; outcomes are E034's `ArgumentRepairOutcome` objects and feed
  `summarize_paired` (E026) unchanged.
- `HFPlanScorer`: the pinned Qwen scorer. The prompt is rendered exactly as the
  E034 pilot rendered it (same system prompt, chat template, generation
  prompt) and tokenised once; those ids are frozen, as they are in generation.
  Each continuation's ids come from the continuation string alone (no special
  tokens), must decode back to it, and are followed by the end-of-turn id. The
  concatenated string is never retokenised, so a plan cannot retroactively
  change the prompt's tokens. The prompt's key/value cache is computed once and
  copied per continuation, so scoring `n` plans costs one prompt forward plus
  `n` short forwards.
- `chance_baselines`, `top_candidate_histogram`: the baselines and the
  position diagnostic above.

Tests cover rotation bookkeeping (a rotated task verifies its own restoring
plan), the attractor reproduction, score ordering, normalisation, cancellation
of a pure position preference under rotation and survival of a content
preference for every answer index, the corrective loop and its E026 feed, the
feasible-only restriction, the analytic baselines, and the HF scorer against an
independent reference that starts from the already-tokenised prompt, including
a tokenizer whose concatenated tokenisation merges across the prompt boundary,
where the reference from `tokenizer(prompt + continuation)` is shown to differ
and is not what the scorer computes. No test downloads weights; the live smoke
is `python examples/run_plan_scoring_mock.py --hf`.

## What this tests, per the contribution rule

1. **Open question**: does the frozen 0.5B generator's likelihood over the
   closed E034 plan space rank the restoring plan above the model-free
   predicate-plus-ranker baseline, and does the fallible recommendation reduce
   corrective turns when the output surface is canonical continuation
   likelihood ranking over the closed plan space?
2. **Deterministic signal**: the unchanged E034 verifier and truth; the analytic
   chance baselines; the rotation histogram.
3. **Comparison**: uniform over the plan space; uniform over binding plans;
   binding plans of a correct recommendation (the ranker-plus-predicate bar);
   E034's 0/64 free-generation result on the same tasks; the length-normalised
   and rotated rankings as secondaries.
4. **Stop condition**: run the 64 E034 pilot tasks baseline-only first, with the
   same label-free sample. If the summed-likelihood top plan is exact on no more
   tasks than the uniform-over-binding-plans expectation, and rotation does not
   change that, the generator does not know the plan either: the E034 boundary
   is capability, not emission, and the next step is a larger generator, as
   E034 already recorded. If it is exact on materially more, canonical plan
   likelihood carries signal the free generation could not express, and the
   paired assisted run is worth its cost. That reading stops short of claiming
   a grammar-constrained decoder would recover the same plans; establishing
   that needs the exhaustive-tokenisation scoring described above, under its
   own preregistration.

## Predictions

- The unrotated ranking will show a strong candidate-1 prior in the histogram,
  and much of it will vanish under rotation. The 0/64 attractor result makes
  the prior likely, and the rotation control is what makes it measurable.
- Summed likelihood will over-select `keep`; the normalised secondary will not.
- If the generator carries any signal, it will show first on the 29 pure-
  selection tasks, where the operation is fixed once the candidate is chosen.

## Out of scope

E027, E031, and E035 (the independent replication of E032 ranked
re-recommendation, which has now completed) are untouched. E036 does not alter
E034's stop decision, its parser, vocabulary, or prompt, and it does not tune
anything on the 64 pilot tasks: the scorer sees the same prompt the pilot used,
and the plan space it ranks is the one E034 already enumerates.
