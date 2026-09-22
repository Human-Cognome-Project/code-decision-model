# E017 — 16M static code encoder

E017 adds `minishlab/potion-code-16M-v2` as an extreme-efficiency backbone.

The model is deliberately different from UniXcoder and CodeRankEmbed:

- about 16M parameters;
- 256-dimensional embeddings;
- MIT licensed;
- distilled from CodeRankEmbed;
- trained further on code retrieval data;
- static token embeddings rather than a transformer forward pass.

The adapter uses Model2Vec's published symmetric encoding path for context, question, and
candidate roles. There is no query prefix or learned runtime backbone state.

## Why it matters

The project began from a local-code constraint. If a 16M static encoder preserves enough
decision signal, repository indexing becomes much cheaper:

~~~text
repository symbol
    -> static 256-d vector
    -> cache
    -> tiny decision scorer
~~~

That would be a qualitatively different deployment target from even a 125-140M transformer
encoder.

## Evaluation gate

Do not compare the model on model-card retrieval numbers. Use the project's own fixed
function+method corpus and report:

- raw cosine;
- two-parameter cosine mixture;
- pairwise MLP head;
- per-task and per-repository accuracy;
- source-clustered uncertainty;
- indexing/inference wall time and cache size.

The performance/efficiency tradeoff is the result of interest.
