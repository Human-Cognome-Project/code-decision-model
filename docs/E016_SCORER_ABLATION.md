# E016 — Scorer capacity ablation

The current decision head is intentionally small relative to a code encoder, but it is still
large enough to overfit the first few hundred machine-labeled decisions.

E016 makes the scorer injectable and adds a deliberately tiny alternative.

## Pairwise MLP

The existing default remains unchanged in behavior:

- context embedding;
- question embedding;
- candidate embedding;
- context × candidate;
- question × candidate;
- absolute context/candidate difference;
- absolute question/candidate difference;
- LayerNorm → hidden layer → scalar score.

It remains the default scorer.

## Cosine mixture

The regularized scorer has only **two trainable scalar parameters**:

1. a sigmoid mixture weight between context/candidate cosine and question/candidate cosine;
2. a positive shared logit scale.

Conceptually:

~~~text
m = sigmoid(mix_logit)
s = exp(log_scale)

score(candidate) =
    s * (
        m       * cosine(context, candidate)
        + (1-m) * cosine(question, candidate)
    )
~~~

No bias is needed because a candidate-independent bias cancels under softmax.

## Why test it

Earlier experiments showed useful zero-shot embedding geometry while the learned MLP head was
unstable on small held-out sets. The tiny scorer asks a cleaner question:

> Is the useful operation mostly already present in the encoder geometry, with only a learned
> mixture/calibration required?

The combined function+method benchmark should compare:

- raw context/candidate cosine;
- the two-parameter cosine mixture;
- the existing pairwise MLP.

If the tiny scorer approaches the MLP with lower seed variance, that is preferable for a local
decision layer until substantially more supervision exists.
