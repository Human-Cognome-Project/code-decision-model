# E043 — Cross-file repository retrieval preregistration

E041 and E042 established that the frozen decision scorer retains useful ranking
signal as candidate sets widen from four choices to complete in-scope and
repository pools. The next practical architecture question is not whether a
hundreds-way scorer has any signal, but whether a cheap, independently cacheable
first stage can recover the target into a bounded shortlist before reranking.

E043 tests that retrieval stage on E030 cross-file calls.

The E030 caller context already omits the module-level import statement and masks
the imported callee as `__CALL_TARGET__`. Retrieval therefore cannot simply read
the import that supplied the deterministic label.

E043 is retrieval-only. It does not train or invoke the PairwiseMLP scorer and
does not call a generator.

## Frozen repositories

Use the exact four E031 repository revisions:

1. AlphaFold — `c77e5d2a8961d1a353632c462914ff0a32a950f6`
2. Pyodide — `e4d3ae954d01d61a3e90531d63b881f2d33361b4`
3. Optuna — `7d08bfa1824606d7caedb80abfd8558bc63826d7`
4. pytest — `6a9ba0f02f827a54cff6ab4da0dddecd65444ff6`

These repositories have already been used for E031/E041/E042, so E043 is an
exploratory mechanism experiment, not a fresh confirmatory generalization test.

## Frozen task extraction

For each repository use:

`repository_hard_masked_cross_file_call_examples(..., candidate_count=4, candidate_body_chars=512, seed=0)`

The extractor's deterministic import resolver supplies the machine label, but
the returned example context contains only the masked caller function. The
module-level import statement is not part of the retrieval query.

Use every extracted cross-file task meeting the repository-pool integrity rules
below. Do not select tasks by model outcome, pool size, or retrieval difficulty.

Report extraction counts by repository before any retrieval result.

## Frozen repository candidate universe

For each task:

1. build E040 `in_scope_pools` for the pinned repository;
2. take `scope.repository_pool(example)`;
3. render candidates at `body_chars=512`;
4. apply the unchanged E024 `CallSiteBindable` predicate;
5. collapse identical rendered candidate texts;
6. exclude only deterministic target-rendering ambiguities.

The labelled target must be present and survive E024. Target absence or predicate
veto is an integrity failure and invalidates the run. Rendering ambiguity is a
deterministic exclusion and must be reported.

There is no candidate-count cutoff.

## Retrieval query

Use exactly the E030 masked caller context after
`focus_hard_call_context(example, radius_lines=0)`.

Do not add:

- the source file's import statements;
- the target alias or real name;
- repository path hints;
- scorer outputs;
- E041/E042 ranks.

The generic E030 question string is not part of the primary retrieval query.
The primary query is code context only.

## Frozen retrievers

### Primary cheap retriever: Potion

Use the existing `PotionCodeEncoder` with
`minishlab/potion-code-16M-v2`.

Encode the focused caller context and every distinct E024-bindable repository
candidate independently. Rank candidates by descending cosine similarity between
the context and candidate embeddings. Ties break by stable candidate order.

Potion candidate embeddings must be deduplicated and cached per repository.

### Frozen reference retriever: CodeRank

Use the existing `CodeRankEncoder(max_length=512, normalize_embeddings=False)`
with `nomic-ai/CodeRankEmbed`.

Encode the focused caller as role `context` and candidates as role
`candidate`. Rank by descending cosine similarity, with stable candidate-order
tie breaking.

This is a retrieval reference, not the trained PairwiseMLP scorer. It answers
whether a stronger frozen code representation changes retrieval viability before
any decision-head reranking.

## Fixed shortlist sizes

Report recall at the following cutoffs, fixed before results:

- 8;
- 16;
- **32 primary**;
- 64.

The primary shortlist size is **32**. It is an operationally bounded first-stage
budget, not a cutoff selected from E042's target-rank diagnostics.

Do not add or change cutoffs after inspecting E043.

## Primary endpoint

For retriever `r` and task `i` with `n_i` bindable repository candidates:

- `hit_i(r, 32) = 1` if the target is in the first 32 retrieved candidates;
- uniform expected recall is `min(32, n_i) / n_i`;
- excess is `hit_i - min(32, n_i)/n_i`.

Report separately for Potion and CodeRank:

- recall@32;
- summed uniform expected hits;
- mean excess over uniform;
- repository-stratified source-file-clustered bootstrap 95% CI for mean excess.

Bootstrap:

- 5,000 replicates;
- resample source files with replacement within repository strata;
- seed **43043**.

## Retrieval viability rule

This is a bounded-retrieval falsifier, not a model-selection bakeoff.

A retriever is considered viable for a later frozen-reranker experiment only if
both are true at the preregistered 32-candidate cutoff:

1. recall@32 is at least **75%**;
2. the clustered 95% CI lower bound for excess over uniform is > 0.

Continuation is deterministic:

- if Potion passes, use Potion as the cheap first-stage candidate in the next
  separately preregistered reranking experiment;
- if Potion fails but CodeRank passes, use CodeRank retrieval and record that the
  16M static retriever was insufficient;
- if both fail, stop these context-cosine retrieval forms and change the retrieval
  representation or deterministic candidate construction before reranking.

Do not choose whichever retriever happens to have the higher observed recall if
both fail the fixed viability rule.

## Secondary diagnostics

Report without altering the gate:

- recall@8, @16, and @64;
- target rank distribution;
- mean reciprocal rank;
- pool-size distribution;
- ambiguity exclusions;
- per-repository recall;
- query-encoding time;
- unique candidate-encoding time and count;
- approximate per-query cosine-ranking time after candidate caching.

Runtime is descriptive and is not a pass condition.

## Leakage / integrity controls

For every retained example assert:

- the masked context contains neither the import alias nor, when different, the
  target's real name;
- the target candidate is unique after bindability and rendering deduplication;
- retrieval receives no module-level import text;
- no E041/E042 scorer rank is used to construct or order the shortlist.

Any violation invalidates the task rather than counting as retrieval failure.

## Out of scope

E043 does not test:

- PairwiseMLP reranking;
- generator behavior;
- end-to-end corrective turns;
- CodeBERT/GraphCodeBERT;
- learned retrieval;
- new predicates;
- scope-filter retrieval using the withheld import.

Those remain separate experiments.

## Interpretation boundary

A pass establishes only that a frozen independently encoded retrieval stage can
recover cross-file targets into a 32-candidate shortlist often enough to justify
testing the frozen decision reranker next.

It does not establish final selection accuracy or reduced corrective burden.
