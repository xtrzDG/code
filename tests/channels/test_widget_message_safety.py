"""
Messages render inert in the widget: a visitor's or the assistant's text is
text, markup in it never becomes elements, and only http(s) addresses
become links, in a new tab with rel="noopener noreferrer nofollow";
javascript: and data: addresses stay text.
"""

import json
import re
import shutil
from typing import Any, cast

import pytest

from tests.channels.widget_node_runner import (
    extract_function,
    extract_variable,
    run_in_node,
)
from tests.channels.widget_script_source import SCRIPT_SOURCE

XSS_PAYLOADS: tuple[str, ...] = (
    "<script>alert(1)</script>",
    '<img src=x onerror="alert(1)">',
    "<svg/onload=alert(1)>",
    '"><iframe src="javascript:alert(1)"></iframe>',
    "javascript:alert(document.cookie)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "{{constructor.constructor('alert(1)')()}}",
    "${alert(1)}",
)
HTML_SINKS: tuple[str, ...] = (
    "innerHTML",
    "outerHTML",
    "insertAdjacentHTML",
    "document.write",
    "eval(",
    "new Function",
    "createContextualFragment",
)
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="needs node")


def render_message(role: str, text: str) -> dict[str, Any]:
    program: str = (
        extract_variable("URL_PATTERN")
        + extract_variable("RTL_CHARACTER_PATTERN")
        + extract_function("el")
        + extract_function("isSafeWebLink")
        + extract_function("appendLinkedText")
        + extract_function("messageRow")
        + f"\nconsole.log(JSON.stringify(describe(messageRow({json.dumps(role)}, "
        f"{json.dumps(text)}, 'ltr', ''))));"
    )
    return cast(dict[str, Any], run_in_node(program))


def nodes_of(tree: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = [tree]
    for child in tree.get("children", []):
        found.extend(nodes_of(child))
    return found


def test_the_widget_never_writes_markup() -> None:
    for sink in HTML_SINKS:
        assert sink not in SCRIPT_SOURCE, sink


@needs_node
@pytest.mark.parametrize("role", ["visitor", "assistant", "staff"])
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_markup_in_a_message_is_text(role: str, payload: str) -> None:
    tree = render_message(role, f"Hello {payload} bye")

    elements = [node for node in nodes_of(tree) if "tag" in node]
    assert {node["tag"] for node in elements} <= {"div", "a"}
    texts = "".join(node["text"] for node in nodes_of(tree) if "text" in node)
    assert texts == f"Hello {payload} bye"
    for link in (node for node in elements if node["tag"] == "a"):
        assert re.match(r"^https?://", link["href"])


@needs_node
def test_a_web_address_becomes_a_safe_link() -> None:
    tree = render_message("assistant", "Menu: https://trattoria.example/menu. Ciao")

    [link] = [node for node in nodes_of(tree) if node.get("tag") == "a"]
    assert link["href"] == "https://trattoria.example/menu"
    assert link["textContent"] == "https://trattoria.example/menu"
    assert link["target"] == "_blank"
    assert link["rel"] == "noopener noreferrer nofollow"


@needs_node
@pytest.mark.parametrize(
    "address",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        "data:text/html,<b>x</b>",
        "vbscript:msgbox(1)",
        "https://",
    ],
)
def test_only_http_addresses_are_links(address: str) -> None:
    program: str = extract_function("isSafeWebLink") + (
        f"\nconsole.log(JSON.stringify(isSafeWebLink({json.dumps(address)})));"
    )

    assert run_in_node(program) is False
    tree = render_message("assistant", f"See {address} now")
    assert not [node for node in nodes_of(tree) if node.get("tag") == "a"]
