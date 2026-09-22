# E032 — Ranked feasible re-recommendation

E028 established the mechanism behind every remaining E027 assisted failure:

1. the scorer recommends the wrong candidate;
2. the generator follows it (400/400 first attempts followed the recommendation);
3. the verifier rejects it;
4. the correction turn still carries the discredited recommendation, and only
   32% of those tasks recover.

E029 turns the rejection into a hard constraint: the rejected candidate leaves
the choice set and the recommendation pointing to it is dropped. The correction
turn then runs with **no** decision evidence.

E032 asks a narrower question: since the scorer already produced a full ranking
when it produced the recommendation, why discard it? At each turn the
recommendation becomes the highest-ranked candidate in the feasible set, where
feasible means it passes every hard constraint (E019, E024) and has not been
rejected by the verifier.

```text
feasible_t      = allowed_by_constraints  and  not rejected_before_t
recommendation_t = first index in ranking that is feasible_t   (None if empty)
```

No new model call is made. Prompt mechanics are exactly E029's, so with no
constraints the first-turn prompt is identical to E027's.

## Two separable effects

| Effect | When it fires | What changes |
| --- | --- | --- |
| turn-0 gating | a hard constraint vetoes the scorer's top choice | the first recommendation is the best non-vetoed candidate |
| post-rejection re-recommendation | the verifier rejects the followed candidate | the next turn recommends the scorer's next feasible candidate |

The trace records both: `gated_at_turn_zero` and the per-attempt
`recommendations`, so a live run can report them separately.

## Prediction from E028

Because the generator follows the recommendation with near-perfect fidelity,
second-turn success on wrong-recommendation tasks under E032 should approach the
scorer's conditional rank-2 accuracy:

```text
P(rank-2 correct | rank-1 wrong) = (top-2 accuracy − top-1 accuracy) / (1 − top-1 accuracy)
```

With E027's 59% top-1 accuracy, a top-2 accuracy of 75% would give 39%, and
80% would give 51%, against the 32% recovery E028 observed under the frozen
prompt. The prediction is falsifiable from the same records once the scorer's
ranking is recomputed (the scorer is deterministic under the frozen protocol;
E027 records store only the recommendation index).

Turn-0 gating is expected to be a small effect on the E027 corpora, where the
E024 predicate vetoes about 3% of candidates, and a large one on E030
cross-file decisions, where it vetoes about 46%.

## Mock

`python examples/run_ranked_memory_mock.py` reproduces the E028 generator
behaviour and shows, on one task:

- the frozen loop re-follows the discredited recommendation and fails;
- E029 drops the recommendation and the generator guesses without evidence;
- E032 recommends the scorer's second choice and succeeds on the correction
  turn;
- with the E024 predicate attached, a vetoed top choice is never recommended
  and the task succeeds on the first attempt.

These mocks prove the plumbing, not the effect.

## What this tests, per the contribution rule

1. **Open question**: after a deterministic rejection, is the scorer's next
   feasible choice better evidence than no evidence?
2. **Deterministic signal**: the E023 structured-edit verifier, unchanged;
   feasibility from the E019 constraint path, unchanged.
3. **Comparison**: E029 rejection memory and the frozen E027 loop, on the same
   wrong-recommendation tasks, with identical first turns when no constraint
   fires.
4. **Stop condition**: abandon if E032 does not beat E029 on
   wrong-recommendation tasks within the two-attempt budget, or if the
   generator stops following recommendations after a rejection so the
   mechanism E028 identified no longer holds.

## Invariants

- first-turn behaviour equals E027 whenever no constraint vetoes the top-ranked
  candidate;
- scorer training and the ranking are unchanged; only which entry is surfaced
  changes;
- no candidate is excluded from the prompt before a deterministic rejection;
- constraint vetoes affect the recommendation only, never the visible choice
  set, so any constraint effect is attributable to the decision layer alone.

## Out of scope

E031 is the frozen replication gate and must not include this. E032 is an
exploratory follow-up to E029 and should run on the E027 records first.
