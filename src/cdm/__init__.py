"""Code Decision Model experimental package."""

from .model import (
    CodeDecisionModel,
    CosineMixScorer,
    EncodedDecisionContext,
    PairwiseMLPScorer,
)
from .text import HashTextEncoder
from .unixcoder import UniXcoderEncoder
from .coderank import CodeRankEncoder
from .potion import PotionCodeEncoder
from .repair import (
    PairedRepairOutcome,
    RepairAttempt,
    RepairOutcome,
    RepairVerification,
    build_repair_prompt,
    expected_repair_source,
    feedback_for,
    run_paired_repair,
    run_repair_loop,
    verify_repair,
)
from .binding import CallShape, CallSiteBindable, Parameters
from .crossfile import repository_hard_masked_cross_file_call_examples
from .corrective import (
    ArmSummary,
    ExactTest,
    PairedCorrectiveSummary,
    PairedInterval,
    cluster_bootstrap_paired,
    exact_mcnemar,
    exact_sign_test,
    render_report,
    summarize_paired,
    summarize_paired_by,
)
from .constraints import (
    AllAllowed,
    ConstrainedDecision,
    Constraint,
    ConstraintResult,
    RejectSubstring,
    RequireSubstring,
    apply_constraints,
)

__all__ = [
    "CodeDecisionModel",
    "CosineMixScorer",
    "EncodedDecisionContext",
    "PairwiseMLPScorer",
    "HashTextEncoder",
    "UniXcoderEncoder",
    "CodeRankEncoder",
    "PotionCodeEncoder",
    "PairedRepairOutcome",
    "RepairAttempt",
    "RepairOutcome",
    "RepairVerification",
    "build_repair_prompt",
    "expected_repair_source",
    "feedback_for",
    "run_paired_repair",
    "run_repair_loop",
    "verify_repair",
    "repository_hard_masked_cross_file_call_examples",
    "ArmSummary",
    "ExactTest",
    "PairedCorrectiveSummary",
    "PairedInterval",
    "cluster_bootstrap_paired",
    "exact_mcnemar",
    "exact_sign_test",
    "render_report",
    "summarize_paired",
    "summarize_paired_by",
    "CallShape",
    "CallSiteBindable",
    "Parameters",
    "AllAllowed",
    "ConstrainedDecision",
    "Constraint",
    "ConstraintResult",
    "RejectSubstring",
    "RequireSubstring",
    "apply_constraints",
]
