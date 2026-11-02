"""
The widget keeps no transcript past its conversation: one idle for a day
is forgotten when the widget loads (the history, its position, the handoff
and the visitor key, which would fetch the old messages back), and a
history saved before its time was stamped starts the idle clock.
"""

import json
import shutil
from typing import Any, cast

import pytest

from tests.channels.widget_node_runner import (
    extract_function,
    extract_variable,
    run_in_node,
)

DAY_MS: int = 24 * 60 * 60 * 1000
NOW_MS: int = 1_790_856_000_000
PREFIX: str = "aw:biz_1:"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")


def load_with(stored: dict[str, str]) -> dict[str, Any]:
    program: str = (
        extract_variable("CONVERSATION_IDLE_EXPIRY_MS")
        + extract_variable("CONVERSATION_STORAGE_KEYS")
        + extract_function("forgetIdleConversation")
        + extract_function("localStorageOrNull")
        + extract_function("storageGet")
        + extract_function("storageSet")
        + extract_function("storageRemove")
        + f"\nvar stored = {json.dumps(stored)};"
        + f"\nvar storagePrefix = {json.dumps(PREFIX)};"
        + "\nvar memoryStorage = {}; var isLivePreview = false;"
        + f"\nDate.now = function () {{ return {NOW_MS}; }};"
        + "\nvar window = { localStorage: {"
        + " getItem: function (k) { return k in stored ? stored[k] : null; },"
        + " setItem: function (k, v) { stored[k] = String(v); },"
        + " removeItem: function (k) { delete stored[k]; } } };"
        + "\nforgetIdleConversation();"
        + "\nconsole.log(JSON.stringify(stored));"
    )
    return cast(dict[str, Any], run_in_node(program))


def conversation(last_at: int) -> dict[str, str]:
    return {
        PREFIX + "session": "v1_" + "a" * 32,
        PREFIX + "history": '[{"role":"visitor","text":"Un tavolo per due?"}]',
        PREFIX + "history-at": str(last_at),
        PREFIX + "cursor": "message_1",
        PREFIX + "handoff": "1",
        PREFIX + "handoff-at": str(last_at),
        PREFIX + "activity-at": str(last_at),
        "aw:biz_2:history": "[]",
    }


def test_a_conversation_idle_for_a_day_is_forgotten() -> None:
    left = load_with(conversation(NOW_MS - DAY_MS - 1))

    # Another business's chat on the same site keeps its own.
    assert left == {"aw:biz_2:history": "[]"}


def test_a_recent_conversation_is_kept() -> None:
    stored = conversation(NOW_MS - DAY_MS + 60_000)

    assert load_with(stored) == stored


def test_a_history_without_a_stamp_starts_the_clock() -> None:
    stored = {PREFIX + "history": "[]", PREFIX + "session": "v1_" + "b" * 32}

    left = load_with(stored)

    assert left == {**stored, PREFIX + "history-at": str(NOW_MS)}
