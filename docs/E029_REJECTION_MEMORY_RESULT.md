# E029 — Deterministic rejection-memory result

E029 tested the E028 follow-up on the original E027 repository set. After the deterministic verifier rejected a candidate, the correction turn removed that candidate from the visible choice set and removed the recommendation pointing to it.

## Provenance

- workflow: `e029-rejection-memory`
- run: `35789543257`
- branch: `analysis/e029-rejection-memory-live`
- head SHA: `71b92478ae42c5eb6ad3b05875a07a4921487424`
- aggregate artifact: `e029-aggregate`
- artifact digest: `sha256:7b11b6626e15e9f08974634c9fc9ed62d9f731fa667c80f56b68e4d08f4519b5`

The live reproduction matched the frozen E027 assisted result exactly before measuring the intervention.

## Result

| Condition | Success within 2 attempts |
| --- | ---: |
| Frozen E027 assisted | 289/400 (72.25%) |
| E029 rejection memory | 292/400 (73.00%) |

Overall delta: **+0.75 percentage points**.

Repository-stratified source-file bootstrap 95% interval: **-0.96 to +2.32 percentage points**.

On the 164 wrong-recommendation tasks:

- frozen E027: 53/164 successful;
- E029: 56/164 successful;
- paired outcomes: 47 both, 9 E029-only, 6 frozen-only, 102 neither;
- exact two-sided McNemar p = **0.6072**.

## Mechanism

E029 nearly eliminated immediate repetition of the verifier-rejected choice:

| Second-turn outcome | Frozen E027 | E029 |
| --- | ---: | ---: |
| correct | 53 | 56 |
| repeated rejected candidate | 20 | 1 |
| different wrong candidate | 91 | 107 |

So the hard memory rule worked mechanically but did not materially improve end-to-end success. Most prevented repetitions became a different wrong choice.

Do not tune E029 further on the four E027 development repositories. E032 is the targeted follow-up: retain rejection memory but surface the scorer's next feasible ranked candidate instead of removing decision evidence entirely.
