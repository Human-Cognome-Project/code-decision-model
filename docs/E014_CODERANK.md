# E014 — CodeRankEmbed adapter

E014 adds a modern compact code-retrieval backbone for comparison with UniXcoder.

The initial target is nomic-ai/CodeRankEmbed:

- 137M parameters;
- MIT license;
- bi-encoder trained for code retrieval;
- 8,192-token context length;
- shared query/code weights;
- query-side instruction prefix required by the published model.

## Role handling

Context and question roles receive the model's published retrieval-query prefix.
Candidate code is encoded without that prefix.

This is why E013 role-aware caching lands first: a candidate cached with query-side
preprocessing would invalidate both retrieval comparisons and decision-head experiments.

## Scope

The adapter intentionally supports frozen inference only. SentenceTransformer.encode is
an inference interface, so pretending it is an end-to-end fine-tuning path would silently
drop gradients. If CodeRankEmbed proves useful, a later experiment can expose a differentiable
backbone path explicitly.

The first comparison should use the same post-2024 repositories, hard masked-call construction,
call-site-focused context, and repository-stratified evaluation already used for UniXcoder.
