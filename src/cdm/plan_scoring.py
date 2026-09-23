"""E035 constrained plan scoring over the E034 closed vocabulary.

E034 stopped at its validity gate: asked to *emit* one plan from a closed
vocabulary, the pinned 0.5B generator produced a valid plan on 11/64 tasks and
the correct one on none, collapsing onto ``candidate 1; keep`` or copying the
first candidate. That result says the generator cannot emit the format. It does
not say whether the generator *knows* the answer.

E035 separates the two. The E034 plan space is finite and enumerable
(:func:`cdm.argument_ops.plan_space`), so instead of sampling text the
generator scores every plan: the log-probability of the rendered plan, followed
by the end-of-turn token, given the E034 prompt. The highest-scoring plan is the
exact maximum a posteriori output under a grammar constraint, which is what a
constrained decoder would return. Format validity is 100% by construction, so
what remains is purely the ranking question:

- does the generator's likelihood put the restoring plan above chance over the
  plan space, and above the deterministic predicate-plus-ranker baseline?
- how much of the ranking is the position prior E034 exposed (candidate 1)?

Nothing about E034's task, verifier, or vocabulary changes. The decision model
is untouched: as in E027, its only role is the recommendation sentence in the
prompt. The corrective turn is deterministic: a verifier-rejected plan is
removed and the next-ranked plan is tried, as E032 does for candidate indices.

Two controls are built in and label-free:

- **length normalisation** (secondary): mean per-token log-probability, since
  the summed score favours the shortest plan, which is always ``keep``;
- **cyclic candidate shifts**: the prompt is re-rendered with the candidates
  rotated and scores are averaged over rotations after mapping plans back, so
  a preference for a candidate *position* cancels while a preference for a
  candidate *content* survives.
"""
from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol

from .argument_ops import (
    ArgumentRepairAttempt,
    ArgumentRepairExample,
    ArgumentRepairOutcome,
    OperationPlan,
    PairedArgumentRepairOutcome,
    build_argument_repair_prompt,
    plan_space,
    predicate_search,
    verify_argument_repair,
)


class PlanScorer(Protocol):
    """Log-probability of each continuation given one prompt.

    Implementations must be deterministic and must not look at anything but
    the prompt and the continuation strings.
    """

    def __call__(self, prompt: str, continuations: Sequence[str]) -> Sequence["ContinuationScore"]:
        ...


@dataclass(frozen=True)
class ContinuationScore:
    log_probability: float
    """Sum of token log-probabilities, including the end-of-turn token."""

    tokens: int
    """Number of scored tokens, including the end-of-turn token."""

    @property
    def mean_log_probability(self) -> float:
        return self.log_probability / self.tokens if self.tokens else float("-inf")


@dataclass(frozen=True)
class ScoredPlan:
    plan: OperationPlan
    score: float
    """Ranking score after any normalisation and shift averaging."""

    log_probability: float
    """Mean summed log-probability over shifts, before normalisation."""

    tokens: float
    """Mean token count over shifts."""


# ---------------------------------------------------------------------------
# Candidate rotation (label-free)
# ---------------------------------------------------------------------------


def cyclic_orders(count: int, shifts: int) -> tuple[tuple[int, ...], ...]:
    """The first ``shifts`` cyclic rotations of ``range(count)``.

    Rotation depends only on the candidate count, never on the label, so the
    set of prompts a task is scored under is a function of visible content.
    """
    if count < 1:
        raise ValueError("count must be positive")
    if not 1 <= shifts <= count:
        raise ValueError("shifts must be between 1 and the candidate count")
    return tuple(tuple((i + s) % count for i in range(count)) for s in range(shifts))


def reorder_item(item: ArgumentRepairExample, order: Sequence[int]) -> ArgumentRepairExample:
    """The same task with candidates presented in ``order``.

    ``order[k]`` is the original index shown at position ``k``. Answer index
    and restoring plan are remapped so the reordered item verifies its own
    restoring plan; the verifier is label-aware, the prompt is not.
    """
    count = len(item.example.candidates)
    if sorted(order) != list(range(count)):
        raise ValueError("order must be a permutation of the candidate indices")
    position = {original: k for k, original in enumerate(order)}
    example = replace(
        item.example,
        candidates=tuple(item.example.candidates[i] for i in order),
        answer_index=position[item.example.answer_index],
    )
    plan = replace(item.restoring_plan, candidate_index=position[item.restoring_plan.candidate_index])
    return replace(item, example=example, restoring_plan=plan)


def shown_position(order: Sequence[int], original_index: int) -> int:
    """Where original candidate ``original_index`` appears under ``order``."""
    return list(order).index(original_index)


def map_plan(plan: OperationPlan, order: Sequence[int]) -> OperationPlan:
    """A plan over the original indices, rendered for the reordered prompt."""
    return replace(plan, candidate_index=shown_position(order, plan.candidate_index))


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_plans(
    item: ArgumentRepairExample,
    scorer: PlanScorer,
    *,
    recommendation_index: int | None = None,
    candidates: Sequence[OperationPlan] | None = None,
    shifts: int = 1,
    normalize: bool = False,
) -> tuple[ScoredPlan, ...]:
    """Every plan in the space (or ``candidates``), best first.

    Ties break by plan-space order, which is candidate index then operation,
    so a scorer that returns constant scores reproduces the E034 attractor
    ``candidate 1; keep`` exactly.
    """
    plans = tuple(candidates) if candidates is not None else plan_space(item)
    if not plans:
        return ()
    count = len(item.example.candidates)
    orders = cyclic_orders(count, shifts)
    totals = [0.0] * len(plans)
    tokens = [0.0] * len(plans)
    for order in orders:
        shown = reorder_item(item, order)
        rec = None if recommendation_index is None else shown_position(order, recommendation_index)
        prompt = build_argument_repair_prompt(shown, recommendation_index=rec)
        continuations = [map_plan(plan, order).render() for plan in plans]
        scores = list(scorer(prompt, continuations))
        if len(scores) != len(plans):
            raise ValueError("scorer must return one score per continuation")
        for i, score in enumerate(scores):
            totals[i] += score.log_probability / len(orders)
            tokens[i] += score.tokens / len(orders)
    ranked = []
    for i, plan in enumerate(plans):
        value = totals[i] / tokens[i] if normalize and tokens[i] else totals[i]
        ranked.append((i, ScoredPlan(plan, value, totals[i], tokens[i])))
    ranked.sort(key=lambda pair: (-pair[1].score, pair[0]))
    return tuple(scored for _, scored in ranked)


# ---------------------------------------------------------------------------
# Loops
# ---------------------------------------------------------------------------


def run_plan_scoring_loop(
    item: ArgumentRepairExample,
    scorer: PlanScorer,
    *,
    recommendation_index: int | None = None,
    max_attempts: int = 3,
    feasible_only: bool = False,
    shifts: int = 1,
    normalize: bool = False,
) -> ArgumentRepairOutcome:
    """Try ranked plans in order until the E034 verifier accepts one.

    Each rejected plan is dropped and the next-ranked plan is the correction,
    so attempt ``k`` is the ``k``-th best plan. ``feasible_only`` restricts
    the ranking to plans that already bind their candidate (E024), which is
    the deterministic layer acting before the generator rather than after.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    candidates = predicate_search(item) if feasible_only else None
    ranked = rank_plans(
        item,
        scorer,
        recommendation_index=recommendation_index,
        candidates=candidates,
        shifts=shifts,
        normalize=normalize,
    )
    prompt = build_argument_repair_prompt(item, recommendation_index=recommendation_index)
    attempts: list[ArgumentRepairAttempt] = []
    for scored in ranked[:max_attempts]:
        output = scored.plan.render()
        verification = verify_argument_repair(item, output)
        attempts.append(ArgumentRepairAttempt(prompt, output, verification))
        if verification.valid:
            return ArgumentRepairOutcome(True, tuple(attempts))
    return ArgumentRepairOutcome(False, tuple(attempts))


def run_paired_plan_scoring(
    item: ArgumentRepairExample,
    scorer: PlanScorer,
    *,
    recommendation_index: int,
    max_attempts: int = 3,
    feasible_only: bool = False,
    shifts: int = 1,
    normalize: bool = False,
) -> PairedArgumentRepairOutcome:
    """Baseline (no recommendation) and assisted arms on the same task."""
    baseline = run_plan_scoring_loop(
        item, scorer, recommendation_index=None, max_attempts=max_attempts,
        feasible_only=feasible_only, shifts=shifts, normalize=normalize,
    )
    assisted = run_plan_scoring_loop(
        item, scorer, recommendation_index=recommendation_index, max_attempts=max_attempts,
        feasible_only=feasible_only, shifts=shifts, normalize=normalize,
    )
    return PairedArgumentRepairOutcome(baseline=baseline, assisted=assisted)


# ---------------------------------------------------------------------------
# Model-free baselines and diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChanceBaselines:
    """Expected first-pass exact success of model-free choosers on one task."""

    uniform: float
    """Uniform over the plan space."""

    feasible_uniform: float
    """Uniform over the plans that bind (E024); zero if the restoring plan does not."""

    recommended_feasible_uniform: float | None
    """Uniform over binding plans of the recommended candidate; None without one."""

    position_prior: float
    """The E034 attractor ``candidate 1; keep``; always 0 because restoring is never keep."""


def chance_baselines(item: ArgumentRepairExample, *, recommendation_index: int | None = None) -> ChanceBaselines:
    space = plan_space(item)
    binding = predicate_search(item)
    restoring = item.restoring_plan
    feasible = 1.0 / len(binding) if binding and restoring in binding else 0.0
    recommended: float | None = None
    if recommendation_index is not None:
        on_rec = [p for p in binding if p.candidate_index == recommendation_index]
        recommended = 1.0 / len(on_rec) if on_rec and restoring in on_rec else 0.0
    attractor = OperationPlan(0, (("keep",),))
    return ChanceBaselines(
        uniform=1.0 / len(space),
        feasible_uniform=feasible,
        recommended_feasible_uniform=recommended,
        position_prior=float(restoring == attractor),
    )


def top_candidate_histogram(rankings: Sequence[Sequence[ScoredPlan]], count: int) -> tuple[int, ...]:
    """How often each candidate position holds the top-ranked plan.

    Under E034's free generation this was ``(64, 0, 0, 0)``. Compared with the
    same histogram under cyclic shifts, it measures the position prior.
    """
    histogram = [0] * count
    for ranked in rankings:
        if ranked:
            histogram[ranked[0].plan.candidate_index] += 1
    return tuple(histogram)


# ---------------------------------------------------------------------------
# Hugging Face scorer (import-guarded; tests inject fakes)
# ---------------------------------------------------------------------------


DEFAULT_SYSTEM_PROMPT = (
    "You are a precise code repair engine. "
    "Answer only with the requested candidate-and-operation plan line."
)
"""The system prompt of the E034 validity pilot, kept verbatim."""


class HFPlanScorer:
    """Score continuations under a causal LM with a shared prompt prefix.

    The prompt is rendered exactly as the E034 pilot rendered it (system
    prompt plus user prompt through the chat template with a generation
    prompt). Its key/value cache is computed once and copied for each
    continuation, so scoring ``n`` plans costs one prompt forward plus ``n``
    short forwards. Each continuation is scored as its tokens followed by the
    end-of-turn token, so the score is the probability of emitting exactly that
    plan and stopping.

    If a continuation does not tokenise as an extension of the prompt's token
    sequence (a merge across the boundary), it is scored with one uncached
    full forward instead; the score is identical, only slower.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-Coder-0.5B-Instruct",
        *,
        revision: str | None = "ea3f2471cf1b1f0db85067f1ef93848e38e88c25",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        use_chat_template: bool = True,
        device: str | None = None,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        if tokenizer is None or model is None:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except ImportError as exc:
                raise ImportError(
                    "HFPlanScorer requires the optional 'hf' dependencies. "
                    "Install with: pip install -e '.[hf]'"
                ) from exc
            if tokenizer is None:
                tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
            if model is None:
                model = AutoModelForCausalLM.from_pretrained(
                    model_name, revision=revision, torch_dtype=torch.float32
                )
                if device is None:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                model = model.to(device)
                model.eval()
        self.tokenizer = tokenizer
        self.model = model
        self.model_name = model_name
        self.revision = revision
        self.system_prompt = system_prompt
        self.use_chat_template = use_chat_template
        self.uncached_fallbacks = 0

    def render_prompt(self, prompt: str) -> str:
        if self.use_chat_template and hasattr(self.tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]
            try:
                return self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except (TypeError, ValueError):
                pass
        if self.system_prompt:
            return self.system_prompt + "\n\n" + prompt
        return prompt

    def _ids(self, text: str) -> list[int]:
        encoded = self.tokenizer(text, return_tensors="pt")
        return [int(i) for i in encoded["input_ids"][0]]

    def _end_token(self) -> int | None:
        eos = getattr(self.tokenizer, "eos_token_id", None)
        return int(eos) if eos is not None else None

    def _device(self):
        return getattr(self.model, "device", None)

    def _forward(self, ids: Sequence[int], cache: Any | None):
        import torch

        tensor = torch.tensor([list(ids)], dtype=torch.long)
        device = self._device()
        if device is not None:
            tensor = tensor.to(device)
        kwargs: dict[str, Any] = {"use_cache": True}
        if cache is not None:
            kwargs["past_key_values"] = cache
        with torch.inference_mode():
            return self.model(input_ids=tensor, **kwargs)

    @staticmethod
    def _sum_log_probs(logits, targets: Sequence[int]) -> float:
        """Log-probability of ``targets`` where ``logits[t]`` predicts ``targets[t]``."""
        import torch

        log_probs = torch.log_softmax(logits.float(), dim=-1)
        index = torch.tensor(list(targets), dtype=torch.long, device=log_probs.device)
        return float(log_probs.gather(-1, index.unsqueeze(-1)).sum())

    def __call__(self, prompt: str, continuations: Sequence[str]) -> list[ContinuationScore]:
        rendered = self.render_prompt(prompt)
        prefix = self._ids(rendered)
        end = self._end_token()
        prefix_out = self._forward(prefix, None)
        prefix_cache = prefix_out.past_key_values
        last_logit = prefix_out.logits[0, -1]

        scores: list[ContinuationScore] = []
        for continuation in continuations:
            full = self._ids(rendered + continuation)
            if end is not None:
                full = full + [end]
            if len(full) > len(prefix) and full[: len(prefix)] == prefix:
                targets = full[len(prefix):]
                # The first target is predicted by the prompt's last position;
                # the rest by the continuation's own positions, fed with the cache.
                total = self._sum_log_probs(last_logit.unsqueeze(0), targets[:1])
                if len(targets) > 1:
                    out = self._forward(targets[:-1], copy.deepcopy(prefix_cache))
                    total += self._sum_log_probs(out.logits[0], targets[1:])
                scores.append(ContinuationScore(total, len(targets)))
                continue
            # Boundary merge: score the whole sequence without the cache.
            self.uncached_fallbacks += 1
            common = 0
            while common < min(len(full), len(prefix)) and full[common] == prefix[common]:
                common += 1
            common = max(common, 1)
            out = self._forward(full[:-1], None)
            targets = full[common:]
            total = self._sum_log_probs(out.logits[0, common - 1 :], targets)
            scores.append(ContinuationScore(total, len(targets)))
        return scores


def make_hf_plan_scorer(**kwargs: Any) -> Callable[[], PlanScorer]:
    """Factory sharing one loaded model across arms, as E022 does."""
    shared: dict[str, Any] = {}

    def factory() -> PlanScorer:
        if "tokenizer" in kwargs or "model" in kwargs:
            return HFPlanScorer(**kwargs)
        if not shared:
            scorer = HFPlanScorer(**kwargs)
            shared["tokenizer"] = scorer.tokenizer
            shared["model"] = scorer.model
            return scorer
        return HFPlanScorer(tokenizer=shared["tokenizer"], model=shared["model"], **kwargs)

    return factory
