# E022 — Live Qwen corrective-turn pilot result

E022 attached a real compact open code generator to the E021 deterministic
corrective-turn harness.

## Fixed setup

Generator:

- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
- parameter class: 0.49B
- greedy decoding
- `max_new_tokens=512`
- maximum 2 generation attempts per arm

Corpus:

- 400 total machine-labelled decisions
- 277 train / 60 validation / 63 held-out test
- 12-example pilot selected from held-out test only
- 3 pilot examples per repository
- 2 function-call and 10 same-class method-call examples

Decision intervention:

- CodeRankEmbed encoder
- `PairwiseMLPScorer(hidden=32)`
- seed 2
- one training epoch
- full 63-example test decision accuracy: 60.3%
- pilot recommendation accuracy: 58.3% (7/12)

The baseline and assisted arms used the same generator and deterministic verifier.
Only the assisted prompt included the fallible decision-model recommendation.

## Result

Neither arm produced a verified repair.

| Condition | First-pass success | Success within 2 attempts | Terminal failures |
| --- | ---: | ---: | ---: |
| Baseline | 0/12 | 0/12 | 12/12 |
| Assisted | 0/12 | 0/12 | 12/12 |

Paired outcomes:

- both succeed: 0
- assisted only: 0
- baseline only: 0
- neither succeeds: 12
- correction-turn delta: not defined

Because no task succeeded in either arm, E022 does **not** provide evidence about
whether the decision layer reduces corrective turns.

## Failure distribution

Across 24 generation attempts in each arm:

Baseline:

- `invalid_python`: 18
- `placeholder_remaining`: 6

Assisted:

- `invalid_python`: 11
- `placeholder_remaining`: 10
- `wrong_function`: 3

The recommendation changed generator behaviour enough to change the failure
distribution, but not enough to cross the deterministic validity threshold.

## Runtime observation

On the GitHub Actions CPU runner:

- baseline generation time: about 870.6 seconds total
- assisted generation time: about 721.2 seconds total

These timings are descriptive only. The pilot was not designed to attribute the
difference to the intervention.

## Interpretation

E022 reached a **generator-validity floor** before it reached the decision-layer
question.

The 0.5B generator was asked to reproduce a complete function while making one
precise edit. It frequently returned invalid Python, retained the placeholder, or
changed the function identity. Since the deterministic verifier correctly rejected
all of these, correction burden could not be compared.

This is not evidence that the decision model failed to help. Seven of the twelve
recommendations were correct, but there were no valid generator repairs on which
that information could produce a measurable turn reduction.

It is also not useful to relax the verifier simply to obtain successes. The verifier
is enforcing the task definition.

## Decision

Do not rerun the same full-function protocol with more threshold tuning or a larger
decision head.

The next bridge experiment, E023, removes the full-function generation confound:
the generator emits only a structured edit intent (candidate 1–4), deterministic
code applies the chosen edit, and the same machine-labelled repository constraint
judges the selection.

That experiment asks the narrower causal question directly:

> Does fallible repository decision evidence reduce wrong-selection correction
> turns when syntax generation is removed from the path?
