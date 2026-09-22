# E010 — Identifier ablation

Hard masked-call recovery removes the true callee name from the caller, but function naming
semantics can still carry substantial information.

That is useful evidence in a real codebase, but it should not be confused with implementation
understanding.

E010 provides controlled transformations for the same labelled examples:

1. full — original hard task;
2. caller-masked — outer caller renamed to __CALLER__;
3. all-own-names-masked — caller renamed and every candidate's own function identifier
   replaced with the same __CANDIDATE__ token.

Candidate bodies retain names of other symbols they call because those are part of the
implementation's relational evidence.

The correct answer and source provenance do not change. This measures how much accuracy comes
from naming semantics versus the remaining code behavior.
