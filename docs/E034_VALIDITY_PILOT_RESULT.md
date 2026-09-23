# E034 — Baseline validity pilot result

E034 asked whether a closed-vocabulary AST-operation surface could preserve the
reliability of index selection while expressing one real argument edit.

The answer for the pinned Qwen 0.5B generator is **no**. The preregistered
validity gate failed before any decision-assisted comparison was run.

## Provenance

- workflow: `e034-validity-pilot`
- run: `35800337140`
- branch: `analysis/e034-validity-pilot`
- head SHA: `4e67ab2175d2736f642222113b36d622acf0a082`
- preregistration commit: `f8f3882dbd5fde93bc0471211b510aaf51e968dc`
- artifact: `e034-validity-pilot`
- artifact digest: `sha256:17d7168287c2ce2ab0aeaca43ef5c5b4a11c6f9dc6ed1f903907b0ae34153500`
- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- revision: `ea3f2471cf1b1f0db85067f1ef93848e38e88c25`
- tasks: 64
- sampling: label-free stable hash with repository × family quota, then global fill
- assistance: none
- corrective turns: none

All selected base examples passed the E034 corruption label-invariance control.

## Overall funnel

| Stage | Count | Rate |
| --- | ---: | ---: |
| Syntax-valid plan | 11/64 | 17.2% |
| Vocabulary-valid plan | 11/64 | 17.2% |
| Applicable operation | 11/64 | 17.2% |
| Bindable edited call | 2/64 | 3.1% |
| Correct candidate | 1/64 | 1.6% |
| Correct restoring operation | 0/64 | 0.0% |
| Exact deterministic repair | 0/64 | 0.0% |

Verifier reasons:

- `invalid_plan`: 53
- `unbindable_call`: 9
- `wrong_target`: 2
- `ok`: 0

Mean generation time was about 6.03 seconds per task on the CPU Actions runner.

For comparison, E033's free-form call-expression pilot produced parse-valid
outputs on 36/64 tasks (56.3%). E034's supposedly easier closed plan surface
fell to 11/64 (17.2%), so it fails the preregistered requirement that format
validity improve substantially over E033.

## Failure mode

This was not primarily a subtle argument-operation error.

Every one of the 64 outputs anchored on **Candidate 1**. Among the 11 outputs
that parsed successfully:

- all 11 selected candidate index 1;
- all 11 emitted exactly the `keep` operation;
- none emitted the hidden restoring operation.

Among the 53 invalid plans:

- 45 copied or began reproducing Candidate 1's signature/body instead of a plan;
- 4 reproduced plan-template placeholders such as `<i>` or `<keyword>`;
- 3 were quoted or near-valid `candidate 1; keep` strings rejected by the strict parser;
- 1 was another malformed schema response.

So constraining the vocabulary did not convert the generator into a reliable
structured-edit emitter. It mostly shifted the failure from free-form code to a
Candidate-1 / no-op attractor.

## Deterministic baseline

The deterministic predicate layer did **not** solve any of the sampled tasks by
itself:

- predicate-alone exact solutions: 0/64;
- pure-selection tasks: 29/64 (45.3%);
- mean plan-space size: 37.19;
- mean binding plans after E024: 8.00;
- mean surviving candidates: 3.83/4.

The 29 pure-selection tasks are informative: on those tasks, bindability had
already reduced argument editing to exactly one binding plan per candidate, so
the remaining problem was effectively target selection. The generator still did
not produce a correct exact plan.

Therefore E034's failure cannot be credited to the deterministic predicate
secretly solving the task, nor does the predicate rescue the generator.

## By task family

| Family | n | Syntax valid | Bindable | Exact | Pure selection |
| --- | ---: | ---: | ---: | ---: | ---: |
| same-file function | 19 | 2 | 0 | 0 | 16 |
| same-class method | 20 | 4 | 0 | 0 | 2 |
| cross-file function | 25 | 5 | 2 | 0 | 11 |

No family crossed a useful validity floor.

## By perturbation

| Perturbation | n | Syntax valid | Bindable | Exact |
| --- | ---: | ---: | ---: | ---: |
| bogus keyword | 50 | 8 | 0 | 0 |
| rename keyword | 6 | 2 | 1 | 0 |
| swap positionals | 8 | 1 | 1 | 0 |

The sample is dominated by `bogus_keyword`, but all three perturbation families
failed exact restoration.

## Interpretation

E034 fails its preregistered validity gate for the pinned Qwen 0.5B generator.

Do **not**:

- proceed to a paired baseline-vs-assisted E034 run with this generator;
- prompt-tune E034 on these 64 tasks;
- loosen the parser or vocabulary after seeing these outputs;
- silently normalize Candidate-1 code/signature responses into plans;
- add deterministic reconstruction that turns a malformed response into the
  hidden operation.

The useful boundary is now sharper:

- this generator is reliable on the structured **candidate-index selection**
  surface used by E023/E027/E031;
- it is not reliable on free-form call generation (E033);
- it is also not reliable on one closed-vocabulary argument-edit operation
  (E034).

For this generator, the demonstrated practical regime is therefore selection,
not generated edit intent.

A future structured-edit experiment should use a materially more capable
generator under a fresh preregistration, rather than create another schema for
Qwen 0.5B.

This result does not weaken E031 or E032, whose successful mechanisms operate on
the index-selection surface.
