"""Tests for E036 constrained plan scoring."""
from __future__ import annotations

import math
import re
from dataclasses import replace

import pytest
import torch
from torch import nn

from cdm.argument_ops import (
    OperationPlan,
    argument_repair_example,
    build_argument_repair_prompt,
    plan_space,
    predicate_search,
    verify_argument_repair,
)
from cdm.corrective import summarize_paired
from cdm.plan_scoring import (
    ChanceBaselines,
    ContinuationScore,
    HFPlanScorer,
    chance_baselines,
    cyclic_orders,
    make_hf_plan_scorer,
    map_plan,
    rank_plans,
    reorder_item,
    run_paired_plan_scoring,
    run_plan_scoring_loop,
    shown_position,
    top_candidate_histogram,
)
from cdm.synthetic import DecisionExample


def _base() -> DecisionExample:
    return DecisionExample(
        context="def caller(value):\n    prepared = value.strip()\n    return __CALL_TARGET__(prepared, 3, strict=True)\n",
        question="q",
        candidates=(
            "normalize(value, depth, strict)\ndef normalize(value, depth=1, strict=False):\n    return value\n",
            "parse(value, depth, **options)\ndef parse(value, depth=1, **options):\n    return value\n",
            "emit(value, level, flag)\ndef emit(value, level=1, flag=False):\n    return value\n",
        ),
        answer_index=0,
        task="python.hard_masked_direct_call",
        source="repo::example.py",
    )


def _item(kind: str = "bogus_keyword", answer_index: int = 0):
    base = _base()
    if answer_index != 0:
        base = replace(base, answer_index=answer_index)
    return argument_repair_example(base, kind=kind)


# ---------------------------------------------------------------------------
# Mock scorers
# ---------------------------------------------------------------------------


class ConstantScorer:
    def __call__(self, prompt, continuations):
        return [ContinuationScore(-1.0, 4) for _ in continuations]


class TableScorer:
    """Scores by continuation text; unknown continuations get the default."""

    def __init__(self, table, default=-10.0):
        self.table = table
        self.default = default
        self.prompts = []

    def __call__(self, prompt, continuations):
        self.prompts.append(prompt)
        return [ContinuationScore(self.table.get(c, self.default), 4) for c in continuations]


class PositionOneScorer:
    """Prefers whatever is shown as candidate 1, regardless of content."""

    def __call__(self, prompt, continuations):
        return [ContinuationScore(0.0 if c.startswith("candidate 1;") else -5.0, 4) for c in continuations]


class ContentOracle:
    """Prefers the plan whose shown candidate contains ``symbol`` and whose op is ``op``."""

    def __init__(self, symbol: str, op: str):
        self.symbol = symbol
        self.op = op

    def __call__(self, prompt, continuations):
        sections = re.split(r"\nCandidate (\d+):\n", prompt)
        shown = {int(sections[i]): sections[i + 1] for i in range(1, len(sections) - 1, 2)}
        scores = []
        for c in continuations:
            k = int(c.split(";")[0].split()[1])
            op = c.split(";")[1].strip()
            good = self.symbol in shown[k].splitlines()[0] and op == self.op
            scores.append(ContinuationScore(0.0 if good else -5.0, 4))
        return scores


# ---------------------------------------------------------------------------
# Rotation
# ---------------------------------------------------------------------------


def test_cyclic_orders_and_position_mapping():
    assert cyclic_orders(3, 1) == ((0, 1, 2),)
    assert cyclic_orders(3, 3) == ((0, 1, 2), (1, 2, 0), (2, 0, 1))
    with pytest.raises(ValueError):
        cyclic_orders(3, 4)
    order = (2, 0, 1)
    assert shown_position(order, 2) == 0 and shown_position(order, 1) == 2
    plan = OperationPlan(1, (("drop", "x"),))
    assert map_plan(plan, order).candidate_index == 2


def test_reordered_item_verifies_its_own_restoring_plan_and_prompt_changes():
    item = _item()
    for order in cyclic_orders(3, 3):
        shown = reorder_item(item, order)
        assert shown.example.candidates[shown.example.answer_index] == item.example.candidates[item.example.answer_index]
        assert verify_argument_repair(shown, shown.restoring_plan.render()).valid
        assert shown.restoring_plan == map_plan(item.restoring_plan, order)
        # The prompt shows the rotated candidates; the caller text is unchanged.
        prompt = build_argument_repair_prompt(shown)
        assert prompt.index("Candidate 1:\n" + shown.example.candidates[0]) > 0
        assert shown.example.context == item.example.context
    with pytest.raises(ValueError):
        reorder_item(item, (0, 0, 1))


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_constant_scores_reproduce_the_e034_attractor():
    item = _item()
    ranked = rank_plans(item, ConstantScorer())
    assert [sp.plan for sp in ranked] == list(plan_space(item))
    assert ranked[0].plan == OperationPlan(0, (("keep",),))


def test_ranking_is_over_exactly_the_plan_space_and_respects_scores():
    item = _item()
    restoring = item.restoring_plan.render()
    scorer = TableScorer({restoring: -0.5, "candidate 2; keep": -0.7})
    ranked = rank_plans(item, scorer)
    assert {sp.plan for sp in ranked} == set(plan_space(item))
    assert ranked[0].plan.render() == restoring
    assert ranked[1].plan.render() == "candidate 2; keep"
    assert len(scorer.prompts) == 1 and "is recommended" not in scorer.prompts[0]
    rank_plans(item, scorer, recommendation_index=2)
    assert "candidate 3 is recommended" in scorer.prompts[-1]


def test_normalisation_uses_mean_per_token():
    item = _item()
    restoring = item.restoring_plan.render()

    class LengthScorer:
        def __call__(self, prompt, continuations):
            # keep is short and gets a better sum; the restoring plan has a better mean.
            return [
                ContinuationScore(-2.0, 2) if c.endswith("; keep") else
                ContinuationScore(-3.0, 6) if c == restoring else ContinuationScore(-9.0, 6)
                for c in continuations
            ]

    assert rank_plans(item, LengthScorer())[0].plan.operation == ("keep",)
    assert rank_plans(item, LengthScorer(), normalize=True)[0].plan.render() == restoring


def test_cyclic_shifts_cancel_position_bias_but_keep_content_preference():
    item = _item()
    # A pure position preference: without shifts it picks candidate 1 (the attractor).
    single = rank_plans(item, PositionOneScorer())
    assert single[0].plan.candidate_index == 0
    # With all rotations every candidate is shown first once; scores tie and
    # fall back to plan-space order, so no candidate is preferred by position.
    shifted = rank_plans(item, PositionOneScorer(), shifts=3)
    assert len({sp.score for sp in shifted}) == 1
    # A content preference survives rotation and maps back to the right index
    # whichever candidate is the target.
    for answer in range(3):
        item_k = _item(answer_index=answer)
        op = " ".join(item_k.restoring_plan.operation)
        symbol = item_k.example.candidates[answer].split("(")[0]
        ranked = rank_plans(item_k, ContentOracle(symbol, op), shifts=3)
        assert ranked[0].plan == item_k.restoring_plan, answer


def test_rotation_invariance_of_a_content_scorer_is_exact():
    item = _item()
    op = " ".join(item.restoring_plan.operation)
    oracle = ContentOracle("normalize", op)
    one = rank_plans(item, oracle, shifts=1)
    three = rank_plans(item, oracle, shifts=3)
    assert [sp.plan for sp in one] == [sp.plan for sp in three]


# ---------------------------------------------------------------------------
# Loops
# ---------------------------------------------------------------------------


def test_loop_tries_ranked_plans_and_counts_corrections():
    item = _item()
    restoring = item.restoring_plan.render()
    scorer = TableScorer({"candidate 2; keep": -0.1, "candidate 3; keep": -0.2, restoring: -0.3})
    outcome = run_plan_scoring_loop(item, scorer, max_attempts=3)
    assert outcome.success and outcome.correction_turns == 2
    assert [a.output for a in outcome.attempts] == ["candidate 2; keep", "candidate 3; keep", restoring]
    assert [a.verification.reason for a in outcome.attempts][-1] == "ok"
    capped = run_plan_scoring_loop(item, scorer, max_attempts=2)
    assert not capped.success and capped.attempts_used == 2
    with pytest.raises(ValueError):
        run_plan_scoring_loop(item, scorer, max_attempts=0)


def test_feasible_only_restricts_to_binding_plans():
    item = _item()
    scorer = TableScorer({"candidate 3; keep": 0.0})  # emit cannot bind strict=
    free = run_plan_scoring_loop(item, scorer, max_attempts=1)
    assert free.attempts[0].verification.reason == "unbindable_call"
    gated = run_plan_scoring_loop(item, scorer, max_attempts=10, feasible_only=True)
    binding = set(predicate_search(item))
    for attempt in gated.attempts:
        assert attempt.verification.reason != "unbindable_call"
        assert OperationPlan(int(attempt.output.split(";")[0].split()[1]) - 1,
                             (tuple(attempt.output.split(";")[1].split()),)) in binding


def test_paired_outcome_feeds_e026():
    item = _item()
    restoring = item.restoring_plan.render()

    class Follower:
        """Ranks the recommended candidate's restoring-op plan first when told."""

        def __call__(self, prompt, continuations):
            rec = "candidate 1 is recommended" in prompt.lower()
            out = []
            for c in continuations:
                if c == restoring:
                    out.append(ContinuationScore(-0.1 if rec else -0.6, 4))
                elif c == "candidate 2; keep":
                    out.append(ContinuationScore(-0.5, 4))
                else:
                    out.append(ContinuationScore(-9.0, 4))
            return out

    paired = run_paired_plan_scoring(item, Follower(), recommendation_index=0, max_attempts=3)
    assert paired.baseline.success and paired.baseline.correction_turns == 1
    assert paired.assisted.first_pass_success
    assert paired.correction_turn_delta == 1
    assert summarize_paired([paired]).correction_turn_deltas == (1,)


# ---------------------------------------------------------------------------
# Baselines and diagnostics
# ---------------------------------------------------------------------------


def test_chance_baselines():
    item = _item()
    space, binding = plan_space(item), predicate_search(item)
    chance = chance_baselines(item)
    assert isinstance(chance, ChanceBaselines)
    assert chance.uniform == pytest.approx(1 / len(space))
    assert chance.feasible_uniform == pytest.approx(1 / len(binding))
    assert chance.recommended_feasible_uniform is None
    assert chance.position_prior == 0.0
    on_target = [p for p in binding if p.candidate_index == 0]
    right = chance_baselines(item, recommendation_index=0)
    assert right.recommended_feasible_uniform == pytest.approx(1 / len(on_target))
    wrong = chance_baselines(item, recommendation_index=1)
    assert wrong.recommended_feasible_uniform == 0.0


def test_top_candidate_histogram():
    item = _item()
    rankings = [rank_plans(item, ConstantScorer()), rank_plans(item, TableScorer({"candidate 3; keep": 0.0}))]
    assert top_candidate_histogram(rankings, 3) == (1, 0, 1)


# ---------------------------------------------------------------------------
# HF scorer with fakes (no network)
# ---------------------------------------------------------------------------


class FakeTokenizer:
    """Word tokenizer whose concatenated tokenisation can merge across a boundary.

    Words are split on whitespace, so ``"ASSISTANT:" + "candidate"`` becomes
    the single token ``"ASSISTANT:candidate"`` when tokenised as one string.
    That is the boundary merge the scorer must never be exposed to.
    """

    eos_token_id = 2
    eos_token = "<eos>"
    pad_token_id = 0

    def __init__(self, template_end: str = "\nASSISTANT:\n"):
        self.template_end = template_end
        self.vocab: dict[str, int] = {}
        self.words: dict[int, str] = {}
        self.special_token_calls: list[bool] = []

    def _id(self, word: str) -> int:
        if word not in self.vocab:
            self.vocab[word] = 3 + len(self.vocab)
            self.words[self.vocab[word]] = word
        return self.vocab[word]

    def __call__(self, text, return_tensors="pt", add_special_tokens=True):
        self.special_token_calls.append(add_special_tokens)
        ids = [self._id(w) for w in re.findall(r"\S+|\n", text)]
        return {"input_ids": torch.tensor([ids], dtype=torch.long)}

    def decode(self, ids, skip_special_tokens=True):
        return " ".join(self.words[int(i)] for i in ids if int(i) in self.words)

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return "SYSTEM:" + messages[0]["content"] + "\nUSER:" + messages[1]["content"] + self.template_end


class _Cache:
    def __init__(self, length: int = 0):
        self.length = length


class _Output:
    def __init__(self, logits, cache):
        self.logits = logits
        self.past_key_values = cache


class BigramModel(nn.Module):
    """Next-token logits depend only on the current token: cache-consistent by construction."""

    def __init__(self, vocab: int = 4096, seed: int = 0):
        super().__init__()
        gen = torch.Generator().manual_seed(seed)
        self.table = nn.Parameter(torch.randn(vocab, vocab, generator=gen), requires_grad=False)
        self.device = torch.device("cpu")
        self.calls: list[tuple[int, int]] = []

    def forward(self, input_ids, past_key_values=None, use_cache=True):
        prior = past_key_values.length if past_key_values is not None else 0
        self.calls.append((prior, input_ids.shape[-1]))
        logits = self.table[input_ids[0]].unsqueeze(0)
        return _Output(logits, _Cache(prior + input_ids.shape[-1]))


def _frozen_prompt_reference(model, tokenizer, rendered, continuation):
    """log P(continuation ids + eos | frozen prompt ids): generation semantics."""
    prompt = tokenizer(rendered)["input_ids"][0].tolist()
    cont = tokenizer(continuation, add_special_tokens=False)["input_ids"][0].tolist() + [tokenizer.eos_token_id]
    logp = torch.log_softmax(model.table, dim=-1)
    sequence = prompt + cont
    total = sum(float(logp[sequence[t - 1], sequence[t]]) for t in range(len(prompt), len(sequence)))
    return total, len(cont)


def _retokenised_string_reference(model, tokenizer, rendered, continuation):
    """The semantics the reviewer rejected: retokenise prompt + continuation as one string."""
    prompt = tokenizer(rendered)["input_ids"][0].tolist()
    full = tokenizer(rendered + continuation)["input_ids"][0].tolist() + [tokenizer.eos_token_id]
    common = 0
    while common < min(len(full), len(prompt)) and full[common] == prompt[common]:
        common += 1
    logp = torch.log_softmax(model.table, dim=-1)
    return sum(float(logp[full[t - 1], full[t]]) for t in range(max(common, 1), len(full)))


def test_hf_scorer_matches_frozen_prompt_reference():
    tokenizer, model = FakeTokenizer(), BigramModel()
    scorer = HFPlanScorer(tokenizer=tokenizer, model=model)
    item = _item()
    prompt = build_argument_repair_prompt(item)
    continuations = [p.render() for p in plan_space(item)[:6]]
    rendered = scorer.render_prompt(prompt)
    assert rendered.startswith("SYSTEM:You are a precise code repair engine.")
    scores = scorer(prompt, continuations)
    scorer_calls = list(tokenizer.special_token_calls)
    for continuation, score in zip(continuations, scores):
        total, tokens = _frozen_prompt_reference(model, tokenizer, rendered, continuation)
        assert score.log_probability == pytest.approx(total, abs=1e-5)
        assert score.tokens == tokens == len(re.findall(r"\S+", continuation)) + 1  # plus end-of-turn
    # One prompt forward, then one short cached forward per continuation.
    assert model.calls[0][0] == 0
    prefix_len = model.calls[0][1]
    assert all(prior == prefix_len for prior, _ in model.calls[1:])
    # The scorer tokenises the prompt once, with special tokens as the pilot
    # did, then each continuation once, without them.
    assert scorer_calls == [True] + [False] * len(continuations)


def test_hf_scorer_never_retokenises_the_prompt_when_the_boundary_would_merge():
    # The template ends without a newline, so tokenising prompt + continuation as
    # one string merges "ASSISTANT:" with "candidate" and changes the prompt's
    # last token. Generation cannot do that: the prompt ids are fixed first.
    tokenizer, model = FakeTokenizer(template_end="\nASSISTANT:"), BigramModel()
    scorer = HFPlanScorer(tokenizer=tokenizer, model=model)
    item = _item()
    prompt = build_argument_repair_prompt(item)
    continuations = [p.render() for p in plan_space(item)[:3]]
    rendered = scorer.render_prompt(prompt)
    prompt_ids = tokenizer(rendered)["input_ids"][0].tolist()
    for continuation in continuations:
        merged = tokenizer(rendered + continuation)["input_ids"][0].tolist()
        assert merged[: len(prompt_ids)] != prompt_ids  # the merge really happens
    before = len(tokenizer.special_token_calls)
    scores = scorer(prompt, continuations)
    # The scorer tokenised the prompt once and each continuation once, alone:
    # the concatenated string was never tokenised.
    assert tokenizer.special_token_calls[before:] == [True] + [False] * len(continuations)
    for continuation, score in zip(continuations, scores):
        frozen, tokens = _frozen_prompt_reference(model, tokenizer, rendered, continuation)
        retokenised = _retokenised_string_reference(model, tokenizer, rendered, continuation)
        assert score.log_probability == pytest.approx(frozen, abs=1e-5)
        assert score.tokens == tokens
        assert score.log_probability != pytest.approx(retokenised, abs=1e-5)


def test_hf_scorer_rejects_a_continuation_that_does_not_round_trip():
    class LossyTokenizer(FakeTokenizer):
        def decode(self, ids, skip_special_tokens=True):
            return "something else"

    scorer = HFPlanScorer(tokenizer=LossyTokenizer(), model=BigramModel())
    with pytest.raises(ValueError, match="round-trip"):
        scorer(build_argument_repair_prompt(_item()), ["candidate 1; keep"])


def test_hf_scorer_end_to_end_ranking_is_deterministic_and_finite():
    tokenizer, model = FakeTokenizer(), BigramModel()
    factory = make_hf_plan_scorer(tokenizer=tokenizer, model=model)
    item = _item()
    a = rank_plans(item, factory(), shifts=3)
    b = rank_plans(item, factory(), shifts=3)
    assert [sp.plan for sp in a] == [sp.plan for sp in b]
    assert all(math.isfinite(sp.score) for sp in a)
    outcome = run_plan_scoring_loop(item, factory(), max_attempts=len(plan_space(item)))
    assert outcome.success  # exhaustive search over the space always reaches the restoring plan
