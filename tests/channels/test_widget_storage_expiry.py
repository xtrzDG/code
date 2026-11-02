"""
The widget keeps no transcript past its conversation: one idle for a day
is forgotten when the widget loads (the history, its position, the handoff
and the visitor key, which would fetch the old messages back), and a
history saved before its time was stamped starts the idle clock. On the
chat page (data-mode="page", the hosted chat) the conversation lives in
the tab's sessionStorage only, and one an earlier version left on the
device is removed.
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


STORAGE_FUNCTIONS: tuple[str, ...] = (
    "forgetIdleConversation",
    "forgetConversationOn",
    "conversationStorageOrNull",
    "localStorageOrNull",
    "sessionStorageOrNull",
    "storageGet",
    "storageSet",
    "storageRemove",
)


def fake_storage(name: str) -> str:
    """A web storage over the JSON object `name`."""

    return (
        f"{{ getItem: function (k) {{ return k in {name} ? {name}[k] : null; }},"
        f" setItem: function (k, v) {{ {name}[k] = String(v); }},"
        f" removeItem: function (k) {{ delete {name}[k]; }} }}"
    )


def run_storage(
    stored: dict[str, str],
    is_page_mode: bool,
    statements: str,
    tab: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run `statements` over a device's (`stored`) and a tab's storage."""

    program: str = (
        extract_variable("CONVERSATION_IDLE_EXPIRY_MS")
        + extract_variable("CONVERSATION_STORAGE_KEYS")
        + "".join(extract_function(name) for name in STORAGE_FUNCTIONS)
        + f"\nvar stored = {json.dumps(stored)};"
        + f"\nvar tab = {json.dumps(tab or {})};"
        + f"\nvar storagePrefix = {json.dumps(PREFIX)};"
        + "\nvar memoryStorage = {}; var isLivePreview = false;"
        + f"\nvar isPageMode = {json.dumps(is_page_mode)};"
        + f"\nDate.now = function () {{ return {NOW_MS}; }};"
        + f"\nvar window = {{ localStorage: {fake_storage('stored')},"
        + f" sessionStorage: {fake_storage('tab')} }};"
        + f"\n{statements}"
        + "\nconsole.log(JSON.stringify({ device: stored, tab: tab }));"
    )
    return cast(dict[str, Any], run_in_node(program))


def load_with(stored: dict[str, str]) -> dict[str, Any]:
    left: dict[str, Any] = run_storage(stored, False, "forgetIdleConversation();")
    assert left["tab"] == {}
    return cast(dict[str, Any], left["device"])


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


def test_the_chat_page_keeps_the_conversation_for_the_tab_only() -> None:
    saved = run_storage(
        {},
        True,
        "storageSet(conversationStorageOrNull(), storagePrefix + 'history', '[]');"
        " storageSet(conversationStorageOrNull(), storagePrefix + 'cursor', 'm_1');"
        " storageSet(localStorageOrNull(), storagePrefix + 'language', 'it');",
    )

    assert saved["tab"] == {PREFIX + "history": "[]", PREFIX + "cursor": "m_1"}
    # What is no transcript (the language) stays on the device.
    assert saved["device"] == {PREFIX + "language": "it"}


def test_a_sites_widget_keeps_the_conversation_on_the_device() -> None:
    saved = run_storage(
        {},
        False,
        "storageSet(conversationStorageOrNull(), storagePrefix + 'history', '[]');",
    )

    assert saved == {"device": {PREFIX + "history": "[]"}, "tab": {}}


def test_the_chat_page_removes_a_conversation_left_on_the_device() -> None:
    device = {**conversation(NOW_MS - 60_000), PREFIX + "language": "it"}
    tab = conversation(NOW_MS - 60_000)

    left = run_storage(device, True, "forgetIdleConversation();", tab)

    assert left["device"] == {"aw:biz_2:history": "[]", PREFIX + "language": "it"}
    # The tab's own recent conversation is kept.
    assert left["tab"] == tab


def test_the_chat_page_forgets_an_idle_conversation_of_the_tab() -> None:
    tab = conversation(NOW_MS - DAY_MS - 1)

    left = run_storage({}, True, "forgetIdleConversation();", tab)

    assert left["tab"] == {"aw:biz_2:history": "[]"}
