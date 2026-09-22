# E029 — Deterministic rejection memory

E028 showed that the E027 assisted generator followed the decision-model
recommendation on 400/400 first attempts. Correct recommendations solved
immediately, while wrong recommendations forced an incorrect first choice.

The correction loop already tells the generator when a chosen candidate is
wrong, but the frozen E027 prompt leaves that rejected candidate—and any
recommendation for it—in the next-turn choice set.

E029 converts that verifier result into a hard environmental constraint.

## Rule

After a candidate is rejected by the deterministic verifier:

1. remove that candidate from the next-turn candidate list;
2. preserve the original candidate numbering;
3. if the decision recommendation points to the rejected candidate, remove the
   recommendation from the next prompt as well;
4. refuse a generator output that names a previously rejected candidate.

In the library harness, the first-turn prompt is exactly the existing E023 prompt.
The live E029 workflow must separately copy the historical E027 live prompt
verbatim; the historical workflow used its own renderer rather than this helper.

## Why this is a hard constraint

This does not add a soft preference such as "try something else." The candidate
has already been deterministically ruled out by the verifier. E029 changes the
next-turn feasible set to reflect that known fact.

This is the same architectural separation intended by E019: learned ranking
proposes; deterministic environmental information can eliminate impossible
choices.

## Primary question

On E027-style wrong-recommendation tasks, does hard rejection memory increase
success within the same two-attempt budget?

The primary paired comparison is:

- frozen assisted loop;
- rejection-memory assisted loop.

Both live arms receive the same recommendation and share one identical first-turn
generation produced from the historical E027 prompt.

## Expected invariants

- first-pass behavior must be identical between arms and reproduce E027;
- scorer training and recommendation indices remain unchanged;
- generator model/revision and greedy decoding remain unchanged;
- maximum attempts remains two;
- no candidate is excluded before a deterministic verifier rejection.

## Falsifier

Abandon the direction if rejection memory does not improve success on
wrong-recommendation tasks under the frozen two-attempt budget.

A small gain limited only to preventing literal repeats is not sufficient reason
to complicate the runtime path unless it also improves verified end-to-end
success.
