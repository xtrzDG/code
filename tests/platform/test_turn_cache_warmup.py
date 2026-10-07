"""
What a worker loads before its lanes take jobs, so the first customer turn
after a deploy costs what every later turn costs (W18-LATENCY-POLISH).
"""

import importlib
import logging
import sys

import pytest

from app.gateways.worker.turn_cache_warmup import warm_turn_caches
from app.utilities.reply_guard.cldr_markers import (
    load_currency_codes,
    load_currency_symbols,
)

STREAMING_HELPERS_MODULE: str = "openai.lib.streaming.responses._responses"


def test_the_reply_guard_markers_are_loaded_before_the_first_turn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    load_currency_symbols.cache_clear()
    load_currency_codes.cache_clear()

    with caplog.at_level(logging.INFO):
        warm_turn_caches()

    assert load_currency_symbols.cache_info().currsize == 1
    assert load_currency_codes.cache_info().currsize == 1
    # The turn reads the cached markers: nothing is loaded again.
    assert "₾" in load_currency_symbols()
    assert load_currency_symbols.cache_info().hits >= 1
    assert "Reply guard markers loaded" in caplog.text


def test_the_model_sdk_responses_resource_is_loaded_with_its_client() -> None:
    # The SDK would import it (and its streaming helpers) on the first call.
    importlib.import_module("app.clients.openai.openai_responses_client")

    assert STREAMING_HELPERS_MODULE in sys.modules
