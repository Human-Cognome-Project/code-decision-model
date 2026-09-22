"""UniXcoder encoder adapter.

Implements the encoder-only representation path used by Microsoft's reference
UniXcoder wrapper while keeping transformers an optional dependency.
"""
from __future__ import annotations

from collections.abc import Iterable

import torch
from torch import nn


class UniXcoderEncoder(nn.Module):
    """Encode code or natural language into UniXcoder sentence representations.

    The adapter exposes the same encoder(list[str]) -> Tensor contract as
    HashTextEncoder, so the decision model does not depend on a particular
    pretrained backbone.

    tokenizer and model are injectable to make the adapter unit-testable without
    downloading a checkpoint.
    """

    def __init__(
        self,
        model_name: str = "microsoft/unixcoder-base",
        *,
        max_length: int = 512,
        frozen: bool = False,
        tokenizer=None,
        model: nn.Module | None = None,
    ) -> None:
        super().__init__()
        if not 4 <= max_length < 1024:
            raise ValueError("max_length must be between 4 and 1023")

        if tokenizer is None or model is None:
            try:
                from transformers import RobertaConfig, RobertaModel, RobertaTokenizer
            except ImportError as exc:
                raise ImportError(
                    "UniXcoderEncoder requires the optional 'hf' dependencies. "
                    "Install with: pip install -e '.[hf]'"
                ) from exc

            tokenizer = tokenizer or RobertaTokenizer.from_pretrained(model_name)
            if model is None:
                config = RobertaConfig.from_pretrained(model_name)
                # Microsoft's reference wrapper enables decoder-capable internals,
                # then supplies a fully bidirectional attention matrix in encoder mode.
                config.is_decoder = True
                model = RobertaModel.from_pretrained(model_name, config=config)

        self.tokenizer = tokenizer
        self.model = model
        self.max_length = max_length
        self.frozen = frozen

        config = getattr(model, "config", None)
        if config is None or not hasattr(config, "hidden_size"):
            raise ValueError("model must expose config.hidden_size")
        self.dim = int(config.hidden_size)

        pad_id = getattr(config, "pad_token_id", None)
        if pad_id is None:
            pad_id = getattr(tokenizer, "pad_token_id", None)
        if pad_id is None:
            raise ValueError("tokenizer/model must expose a pad token id")
        self.pad_token_id = int(pad_id)

        if frozen:
            for parameter in self.model.parameters():
                parameter.requires_grad_(False)
            self.model.eval()

    def _token_ids(self, text: str) -> list[int]:
        tokens = self.tokenizer.tokenize(text)
        tokens = tokens[: self.max_length - 4]
        tokens = [
            self.tokenizer.cls_token,
            "<encoder-only>",
            self.tokenizer.sep_token,
            *tokens,
            self.tokenizer.sep_token,
        ]
        ids = self.tokenizer.convert_tokens_to_ids(tokens)
        if len(ids) > self.max_length:
            raise AssertionError("UniXcoder token construction exceeded max_length")
        return list(ids)

    def _device(self) -> torch.device:
        try:
            return next(self.model.parameters()).device
        except StopIteration:
            return torch.device("cpu")

    def encode_many(self, texts: Iterable[str]) -> torch.Tensor:
        sequences = [self._token_ids(text) for text in texts]
        if not sequences:
            return torch.empty((0, self.dim), device=self._device())

        width = max(len(ids) for ids in sequences)
        source_ids = torch.full(
            (len(sequences), width),
            self.pad_token_id,
            dtype=torch.long,
            device=self._device(),
        )
        for row, ids in enumerate(sequences):
            source_ids[row, : len(ids)] = torch.tensor(
                ids,
                dtype=torch.long,
                device=source_ids.device,
            )

        valid = source_ids.ne(self.pad_token_id)
        # Reference UniXcoder encoder mode uses a full token-to-token mask.
        attention = valid.unsqueeze(1) & valid.unsqueeze(2)

        if self.frozen:
            self.model.eval()
            with torch.no_grad():
                hidden = self.model(
                    source_ids,
                    attention_mask=attention,
                ).last_hidden_state
        else:
            hidden = self.model(
                source_ids,
                attention_mask=attention,
            ).last_hidden_state

        weights = valid.unsqueeze(-1).to(hidden.dtype)
        return (hidden * weights).sum(1) / weights.sum(1).clamp_min(1.0)

    def forward(self, texts: Iterable[str]) -> torch.Tensor:
        return self.encode_many(texts)
