"""
A site's widget writes nothing to the site's storage until the visitor
opens or uses the chat (CONS-07): its visitor key is made on first use and
an existing one is only read; a key no message ever used leaves the device
when the widget loads; the page's visit source is kept only once the
visitor opens or uses the chat. The chat page (data-mode="page", the
hosted chat) is the chat the visitor opened: it has its key, for the tab,
at once.
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

NOW_MS: int = 1_790_856_000_000
PREFIX: str = "aw:biz_1:"
KEY: str = "v1_" + "a" * 32

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")

FUNCTIONS: tuple[str, ...] = (
    "loadSessionKey",
    "ensureSessionKey",
    "forgetIdleConversation",
    "forgetConversationOn",
    "conversationStorageOrNull",
    "localStorageOrNull",
    "sessionStorageOrNull",
    "storageGet",
    "storageSet",
    "storageRemove",
    "randomString",
    "loadVisitSource",
    "keepVisitSource",
    "readPageParameter",
)
VARIABLES: tuple[str, ...] = (
    "CONVERSATION_IDLE_EXPIRY_MS",
    "CONVERSATION_STORAGE_KEYS",
    "SESSION_KEY_PATTERN",
    "SESSION_KEY_ALPHABET",
    "MAX_SOURCE_LENGTH",
)


def fake_storage(name: str) -> str:
    return (
        f"{{ getItem: function (k) {{ return k in {name} ? {name}[k] : null; }},"
        f" setItem: function (k, v) {{ {name}[k] = String(v); }},"
        f" removeItem: function (k) {{ delete {name}[k]; }} }}"
    )


def run_widget(
    statements: str,
    device: dict[str, str] | None = None,
    is_page_mode: bool = False,
    search: str = "",
) -> dict[str, Any]:
    """Run `statements`; the device's and the tab's storage, and `result`."""

    program: str = (
        "".join(extract_variable(name) for name in VARIABLES)
        + "".join(extract_function(name) for name in FUNCTIONS)
        + f"\nvar stored = {json.dumps(device or {})}; var tab = {{}};"
        + f"\nvar storagePrefix = {json.dumps(PREFIX)};"
        + "\nvar memoryStorage = {}; var isLivePreview = false; var result = null;"
        + f"\nvar isPageMode = {json.dumps(is_page_mode)};"
        + f"\nDate.now = function () {{ return {NOW_MS}; }};"
        + "\nvar script = { getAttribute: function () { return null; } };"
        + f"\nvar window = {{ localStorage: {fake_storage('stored')},"
        + f" sessionStorage: {fake_storage('tab')},"
        + f" location: {{ search: {json.dumps(search)} }},"
        + " crypto: { getRandomValues: function (values) {"
        + " for (var i = 0; i < values.length; i += 1) { values[i] = i; }"
        + " return values; } } };"
        + "\nvar visitSource = loadVisitSource();"
        + f"\n{statements}"
        + "\nconsole.log(JSON.stringify({ device: stored, tab: tab, result: result }));"
    )
    return cast(dict[str, Any], run_in_node(program))


def test_loading_on_a_site_writes_nothing() -> None:
    loaded = run_widget("result = loadSessionKey();", search="?utm_source=qr_table")

    assert loaded == {"device": {}, "tab": {}, "result": ""}


def test_the_first_use_makes_and_stores_the_key() -> None:
    used = run_widget(
        "var first = ensureSessionKey(loadSessionKey());"
        " result = [first, ensureSessionKey(first)];"
    )

    first, again = used["result"]
    assert first.startswith("v1_") and len(first) == 35
    assert again == first
    assert used["device"] == {PREFIX + "session": first}


def test_an_existing_key_is_read_and_another_tabs_key_adopted() -> None:
    device = {
        PREFIX + "session": KEY,
        PREFIX + "history": "[]",
        PREFIX + "history-at": str(NOW_MS),
    }

    used = run_widget("result = [loadSessionKey(), ensureSessionKey('')];", device)

    assert used["result"] == [KEY, KEY]
    assert used["device"] == device


def test_a_key_another_tab_dropped_is_stored_again_on_use() -> None:
    used = run_widget(f"result = ensureSessionKey({json.dumps(KEY)});")

    assert used["device"] == {PREFIX + "session": KEY}


def test_a_key_no_message_used_leaves_the_device_on_load() -> None:
    unused = run_widget("result = loadSessionKey();", {PREFIX + "session": KEY})
    handed_off = {PREFIX + "session": KEY, PREFIX + "handoff": "1"}
    positioned = {PREFIX + "session": KEY, PREFIX + "cursor": "message_1"}

    assert unused == {"device": {}, "tab": {}, "result": ""}
    assert run_widget("result = loadSessionKey();", handed_off)["result"] == KEY
    assert run_widget("result = loadSessionKey();", positioned)["result"] == KEY


def test_the_visit_source_is_kept_only_once_the_visitor_engages() -> None:
    engaged = run_widget("keepVisitSource();", search="?src=qr_table")

    assert engaged["tab"] == {PREFIX + "source": "qr_table"}
    assert engaged["device"] == {}


def test_the_chat_page_has_its_key_and_source_for_the_tab_at_once() -> None:
    loaded = run_widget(
        "result = loadSessionKey();", is_page_mode=True, search="?src=qr"
    )

    assert loaded["device"] == {}
    assert loaded["tab"] == {
        PREFIX + "session": loaded["result"],
        PREFIX + "source": "qr",
    }
    assert loaded["result"].startswith("v1_")
