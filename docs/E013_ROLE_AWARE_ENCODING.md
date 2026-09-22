# E013 — Role-aware encoding

The decision architecture already separates context, question, and candidate objects. The
encoder interface should preserve that distinction.

Most encoders can ignore role and continue to use a symmetric embedding space. Retrieval
encoders may require asymmetric preprocessing, such as a query instruction for context/question
representations and an unprefixed code representation for candidates.

E013 adds an optional encoder method:

    encode_role(texts, role="context" | "question" | "candidate")

CodeDecisionModel uses it when available and falls back to the legacy encoder forward method
otherwise.

The frozen representation cache is also keyed by (role, text). This matters when identical text
appears in different semantic roles: a role-aware encoder may legitimately map it to different
vectors.

This makes asymmetric code-retrieval models usable without contaminating the candidate cache
with query-form embeddings.
