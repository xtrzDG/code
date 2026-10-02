"""The example exchanges (few-shot) every niche template shows the model."""

import re

import pytest

from app.registries.niches.niche_template_registry import NicheTemplateRegistry
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.niches import ExampleExchangeKind
from app.schemas.dto.niches import NicheTemplate

TEMPLATES: list[NicheTemplate] = NicheTemplateRegistry().list_all()
NON_ASCII: re.Pattern[str] = re.compile(r"[^\x00-\x7F]")
TOOL_IN_BRACKETS: re.Pattern[str] = re.compile(
    r"\[(?:only after a clear yes: )?([a-z_]+)"
)
TOOL_NAMES: set[str] = {tool.value for tool in AssistantToolName}


def template_id(template: NicheTemplate) -> str:
    return template.key.value


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_every_niche_shows_two_or_three_distinct_exchanges(
    template: NicheTemplate,
) -> None:
    kinds: list[ExampleExchangeKind] = [
        exchange.kind for exchange in template.example_exchanges
    ]

    assert 2 <= len(kinds) <= 3
    assert len(set(kinds)) == len(kinds)
    assert ExampleExchangeKind.PRICE_NOT_FOUND in kinds
    assert ExampleExchangeKind.HANDOFF in kinds


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_niches_without_bookings_confirm_requests_instead(
    template: NicheTemplate,
) -> None:
    kinds: set[ExampleExchangeKind] = {
        exchange.kind for exchange in template.example_exchanges
    }

    if not template.takes_bookings:
        assert ExampleExchangeKind.BOOKING_CONFIRMATION not in kinds
        assert ExampleExchangeKind.REQUEST_CONFIRMATION in kinds

    assert kinds & {
        ExampleExchangeKind.BOOKING_CONFIRMATION,
        ExampleExchangeKind.REQUEST_CONFIRMATION,
    }


@pytest.mark.parametrize("template", TEMPLATES, ids=template_id)
def test_examples_are_plain_english_and_name_real_tools(
    template: NicheTemplate,
) -> None:
    for exchange in template.example_exchanges:
        assistant_line: str = str(exchange.assistant_line)
        named_tools: list[str] = TOOL_IN_BRACKETS.findall(assistant_line)

        assert NON_ASCII.search(str(exchange.customer_line)) is None
        assert NON_ASCII.search(assistant_line) is None
        assert named_tools != []
        assert set(named_tools) <= TOOL_NAMES
        assert "http" not in assistant_line
