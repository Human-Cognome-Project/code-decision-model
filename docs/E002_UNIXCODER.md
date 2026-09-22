# E002 — Pretrained code representation adapter

The first real backbone candidate is **microsoft/unixcoder-base**.

Why start here:

- it is an encoder-capable code model rather than a generator;
- the published model is Apache-2.0;
- its representation training used code, comments, and AST-derived structure;
- Microsoft's reference implementation exposes sentence embeddings directly;
- the checkpoint has a larger positional window than the older GraphCodeBERT base model.

The adapter reproduces UniXcoder's encoder-only input convention:

~~~text
<s> <encoder-only> </s> ...tokens... </s>
~~~

and its fully bidirectional attention mask before mean-pooling token states.

The default smoke path keeps the backbone frozen. That separates two questions:

1. Do the pretrained code representations already contain useful evidence for dynamic decisions?
2. If not, how much task-specific fine-tuning is required?

Do not interpret an untrained decision head's probabilities as meaningful.

Run the integration smoke test with:

~~~bash
pip install -e ".[hf]"
python examples/unixcoder_smoke.py
~~~

A real E002 benchmark will use held-out machine-labeled repository decisions rather than the
handwritten smoke example.
