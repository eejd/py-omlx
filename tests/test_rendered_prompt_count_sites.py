# SPDX-License-Identifier: Apache-2.0
"""Token counts reported for a rendered chat prompt must match what the scheduler prefills.

The /v1/messages/count_tokens endpoint and the admin cache probe render the chat
template and count tokens; a BOS-owning template (Llama 3) must be counted with one
BOS, exactly as ``BatchedEngine`` hands it to the scheduler. Raw ``/v1/completions``
prompts are not chat renders and keep the tokenizer's special-token default.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import PreTrainedTokenizerFast

import omlx.admin.routes as admin_routes
import omlx.server as server
from omlx.api.anthropic_models import AnthropicMessage, TokenCountRequest

BOS = "<|begin_of_text|>"
RENDERED = f"{BOS}hello world"  # what a Llama-3 template renders


def _tokenizer():
    vocab = {"[UNK]": 0, BOS: 1, "hello": 2, "world": 3}
    backend = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    backend.post_processor = TemplateProcessing(
        single=f"{BOS} $A", special_tokens=[(BOS, 1)]
    )
    tok = PreTrainedTokenizerFast(
        tokenizer_object=backend, unk_token="[UNK]", bos_token=BOS
    )
    tok.apply_chat_template = lambda messages, **kw: RENDERED
    return tok


def test_count_tokens_endpoint_counts_one_bos():
    engine = SimpleNamespace(tokenizer=_tokenizer())
    request = TokenCountRequest(
        model="m", messages=[AnthropicMessage(role="user", content="hi")]
    )
    with (
        patch.object(server, "get_engine_for_model", AsyncMock(return_value=engine)),
        patch.object(server, "_raise_if_llm_lease_abort_requested", AsyncMock()),
        patch.object(server, "_server_state", SimpleNamespace(oq_manager=None)),
    ):
        response = asyncio.run(server.count_anthropic_tokens(request, _=True))
    assert response.input_tokens == 3  # BOS, hello, world (default encode gives 4)


def test_admin_cache_probe_counts_one_bos():
    tokenizer = _tokenizer()
    engine = SimpleNamespace(
        _tokenizer=tokenizer,
        _apply_chat_template=lambda msgs, tools, **kw: RENDERED,
        _engine=SimpleNamespace(
            engine=SimpleNamespace(
                scheduler=SimpleNamespace(
                    block_aware_cache=SimpleNamespace(block_size=4),
                    paged_ssd_cache_manager=SimpleNamespace(
                        _hot_cache={},
                        _index=SimpleNamespace(contains=lambda h: False),
                    ),
                    paged_cache_manager=SimpleNamespace(model_name="/m"),
                    config=SimpleNamespace(paged_cache_block_size=4),
                )
            )
        ),
    )
    pool = MagicMock(spec=[])
    pool._entries = {"m": SimpleNamespace(engine=engine)}
    request = admin_routes.CacheProbeRequest(
        model_id="m", messages=[{"role": "user", "content": "hello"}]
    )
    with patch.object(admin_routes, "_get_engine_pool", return_value=pool):
        result = asyncio.run(admin_routes.probe_cache(request, is_admin=True))
    assert result["total_tokens"] == 3
