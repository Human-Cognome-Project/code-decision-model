# Experimental results

This file is the durable record of the project's empirical sequence.

The project is exploratory. Values below are observations from fixed experiments, **not
performance claims**. In particular, small source-group counts can make apparently large
accuracy differences unstable.

## Reproducibility corpus

The current "recent code" experiments use exact revisions rather than moving default branches:

| Repository | Commit |
| --- | --- |
| browser-use/browser-use | `d8110c5ff87ccba887aaa726cdb780f2f84bef8d` |
| unclecode/crawl4ai | `862f6bccb9c063f49b9d42701baa0eea17a4993f` |
| microsoft/markitdown | `b8f79c57ebc0044be41323d89b2a45d3fda8460e` |
| D4Vinci/Scrapling | `08f107b1240fd72847b0f5e10426c7e6cc16e67e` |

Unless noted otherwise, hardened call-recovery experiments use deterministic candidate order,
source-file-disjoint splits, and parser-derived labels.

## E005 pilot — useful result, invalid semantic interpretation

Actions run: `35740572610`

Click masked-call recovery, 16 candidates, 57 train / 5 validation / 37 test:

| Method | Test accuracy |
| --- | ---: |
| Random expectation | 6.25% |
| Lexical overlap | 10.8% |
| Raw UniXcoder cosine | 16.2% |
| Frozen UniXcoder + decision head, mean of 5 seeds | 30.3% |
| Best decision-head seed | 40.5% |

This initially looked encouraging. A later structural baseline using same-file locality and call
arity reached **32.4%**, explaining the mean learned-head score. The result is retained as a
pipeline milestone, not evidence of semantic code judgment.

That failure motivated E006-E008.

## Hardened top-level calls

E006 constrains candidates to the caller's file and the target's structural invocation shape.
E008 additionally controls required/optional positional and keyword-only parameters, variadic
flags, async/sync status, nested-scope attribution, and residual target-name leakage.

### Post-2024 4-way corpus

The fixed recent-code corpus yields:

| Repository | Examples | Source files |
| --- | ---: | ---: |
| browser-use | 68 | 4 |
| crawl4ai | 65 | 26 |
| markitdown | 11 | 5 |
| scrapling | 2 | 2 |
| **Total** | **146** | |

## Call-site context focusing

Actions run: `35747171544`

Zero-shot accuracy across all 146 recent-code examples:

| Context | Lexical | UniXcoder cosine | Marker truncated |
| --- | ---: | ---: | ---: |
| Full caller | 50.68% | 52.05% | 8 |
| Radius 16 | 51.37% | 52.74% | 4 |
| Radius 8 | 50.00% | 54.11% | 4 |
| Radius 4 | 45.89% | 55.48% | 4 |
| Radius 2 | 47.26% | 56.16% | 1 |
| **Call-site only (radius 0)** | **47.26%** | **58.22%** | **1** |

Reducing irrelevant caller context improved UniXcoder while slightly reducing the lexical
baseline. Current experiments therefore use radius-0 context unless the experiment specifically
studies context length.

## Identifier ablation

Actions run: `35749657867`

4-way hard calls, radius-0 context, all 146 recent-code examples:

| Representation | Full | Caller name masked | Candidate own names masked | Both masked |
| --- | ---: | ---: | ---: | ---: |
| Lexical | 47.26% | 47.26% | 47.26% | 47.26% |
| UniXcoder cosine | 58.22% | 51.37% | 51.37% | **50.00%** |
| CodeRankEmbed cosine | 57.53% | 50.00% | 54.11% | **45.21%** |

Random expectation is 25%.

Own-function identifiers provide useful signal, but they do not explain the complete embedding
result: both encoders remain substantially above random after caller and candidate own names are
removed. The unchanged lexical score shows that its evidence comes from remaining body/local
identifiers rather than the ablated own-function names.

## UniXcoder vs CodeRankEmbed

Actions run: `35749453832`

Same fixed corpus, radius-0 context, repository-stratified split:
111 train / 19 validation / 16 test, 4 candidates.

The test set is too small for a backbone verdict; source-clustered intervals are correspondingly
wide. Values are retained because they motivate larger-data experiments.

### Zero-shot cosine

| Encoder | Micro test | Repository macro |
| --- | ---: | ---: |
| UniXcoder | **68.75%** | **60.00%** |
| CodeRankEmbed | 56.25% | 45.56% |

Lexical test accuracy was 50%; random expectation 25%.

### Learned decision head

Five independently initialized 32-hidden-unit heads were trained over frozen representations.

| Encoder | Mean | Std. dev. | Min | Max | Repo-macro mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| UniXcoder | 50.00% | 10.46 pp | 37.50% | 68.75% | 48.44% |
| CodeRankEmbed | **63.75%** | **6.12 pp** | 56.25% | 68.75% | **57.33%** |

Directionally, UniXcoder has stronger raw code-to-code geometry while CodeRankEmbed's
representations were more stable under the current learned head. The 16-example test set is not
large enough to establish that this difference generalizes.

## Same-class method supervision

Actions census run: `35750215072`

E015 adds parser-derived same-class method decisions while controlling receiver/binding type and
invocation shape.

4-way density on the fixed recent-code corpus:

| Repository | Functions | Methods | Combined |
| --- | ---: | ---: | ---: |
| browser-use | 68 | 142 | 210 |
| crawl4ai | 65 | 95 | 160 |
| markitdown | 11 | 6 | 17 |
| scrapling | 2 | 11 | 13 |
| **Total** | **146** | **254** | **400** |

The repository-stratified source-file-disjoint combined split is:

- train: 277
- validation: 60
- test: 63
- test source groups: 8

This is the first evaluation corpus large enough to make the learned-head comparison materially
less dependent on a handful of individual examples, although eight test source files still
requires grouped uncertainty reporting.

## Current open question

The next gate is the combined function+method benchmark over these 400 decisions:

1. Does the frozen zero-shot embedding signal survive the expanded task?
2. Does CodeRankEmbed's apparent learned-head stability survive a 63-example test set?
3. Does training one head over both functions and methods help both task types, or merely average
   two different problems?
4. Are the source-clustered uncertainty intervals narrow enough to justify changing the default
   backbone or scorer?

Only after those questions are answered should scorer complexity or encoder fine-tuning be
increased.
