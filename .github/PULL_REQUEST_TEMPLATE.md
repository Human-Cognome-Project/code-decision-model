## Summary

Briefly describe what this PR does and why.

## Advances

- [ ] End-to-end corrective-turn measurement
- [ ] Hard constraint / validator interface
- [ ] Cross-file or harder decision types under existing integrity controls
- [ ] Leaner scorer or encoder path
- [ ] Better evaluation statistics or integrity controls
- [ ] Documentation / contributor experience only
- [ ] Other (explain):

## Invariants checklist

- [ ] Independent encoding of context, question, and candidates is preserved
- [ ] New supervision (if any) is machine-verifiable or clearly marked otherwise
- [ ] Decision head remains lean (or an ablation justifies any increase)
- [ ] No external theory, soft predicates, or narrative framing introduced
- [ ] Core CPU tests still pass without model downloads

## Measurement impact

Does this change move us closer to, or further from, the practical success criterion  
(fewer corrective turns when a small generator is paired with the decision model)?

## Test plan

How was this tested?
