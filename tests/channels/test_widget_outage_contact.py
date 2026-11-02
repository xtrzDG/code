"""
When the chat cannot answer (switched off, the assistant not live, the API
failing or out of reach), the widget offers the business's phone under the
failed message (REL-04): its public phone from the config, else the
assistant's phone line, never anything that is not an E.164 number.
"""

import re

from app.schemas.dto.channels.widget import WidgetConfigView
from tests.channels.widget_script_source import SCRIPT_SOURCE


def function_body(name: str) -> str:
    start: int = SCRIPT_SOURCE.index(f"function {name}(")
    end: int = SCRIPT_SOURCE.index("\n    }\n", start)
    return SCRIPT_SOURCE[start:end]


def test_the_config_field_the_widget_reads_exists() -> None:
    assert "business_phone_number" in WidgetConfigView.model_fields
    assert "config.business_phone_number" in SCRIPT_SOURCE


def test_outages_are_the_refusals_the_chat_cannot_get_past() -> None:
    body: str = function_body("isOutage")

    assert re.search(r"statusCode === 404", body)
    assert re.search(r"statusCode === 409", body)
    assert re.search(r"statusCode >= 500", body)
    assert "429" not in body
    assert "413" not in body


def test_a_failed_message_in_an_outage_offers_the_phone() -> None:
    render: str = function_body("renderLog")
    contact: str = function_body("fallbackContact")

    assert "item.isOutage ? fallbackContact() : null" in render
    assert 'link.href = "tel:" + number;' in contact
    assert 'text("otherWays")' in contact
    assert 'text("call")' in contact
    assert "textContent" in contact
    assert "innerHTML" not in contact
    # A network failure is an outage too: the API may be down.
    assert SCRIPT_SOURCE.count("item.isOutage = ") == 2


def test_only_an_e164_number_becomes_a_link() -> None:
    match = re.search(r"var PHONE_NUMBER_PATTERN = /(.+)/;", SCRIPT_SOURCE)
    assert match is not None
    pattern = re.compile(match.group(1).replace("\\/", "/"))

    assert pattern.fullmatch("+390612345678")
    for refused in ("390612345678", "+39 06 1234", "javascript:alert(1)", "+1"):
        assert pattern.fullmatch(refused) is None
