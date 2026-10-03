"""
The example exchanges of the instruction (few-shot), composed by code.

A niche shows two or three short exchanges: confirming a booking (or taking
a request), a price that is not in the price list, and a handoff. An
exchange is shown only when the version has the tool it demonstrates, so a
business that cannot book directly never sees a booking example.
"""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.niches import ExampleExchangeKind
from app.schemas.dto.niches import NicheExampleExchange

EXAMPLE_TOOLS: dict[ExampleExchangeKind, AssistantToolName] = {
    ExampleExchangeKind.BOOKING_CONFIRMATION: AssistantToolName.CREATE_BOOKING,
    ExampleExchangeKind.REQUEST_CONFIRMATION: AssistantToolName.CREATE_LEAD,
    ExampleExchangeKind.PRICE_NOT_FOUND: AssistantToolName.GET_PRICE,
    ExampleExchangeKind.HANDOFF: AssistantToolName.HANDOFF_TO_HUMAN,
}
EXAMPLE_TITLES: dict[ExampleExchangeKind, str] = {
    ExampleExchangeKind.BOOKING_CONFIRMATION: "Confirming a booking",
    ExampleExchangeKind.REQUEST_CONFIRMATION: "Taking a request",
    ExampleExchangeKind.PRICE_NOT_FOUND: "A price that is not in the price list",
    ExampleExchangeKind.HANDOFF: "Handing off",
}


def select_examples(
    exchanges: Sequence[NicheExampleExchange],
    tools: Sequence[AssistantToolName],
) -> list[NicheExampleExchange]:
    """The exchanges whose tool the version has, in template order."""

    return [exchange for exchange in exchanges if EXAMPLE_TOOLS[exchange.kind] in tools]


def build_example_section(
    exchanges: Sequence[NicheExampleExchange],
    tools: Sequence[AssistantToolName],
) -> list[str]:
    """Example exchanges, or nothing when none applies."""

    shown: list[NicheExampleExchange] = select_examples(exchanges, tools)
    if not shown:
        return []

    lines: list[str] = [
        "# Example exchanges",
        "They show how to behave, not what is true: take every name, date, time "
        "and price from the customer, the facts and tool results, never from "
        "these examples. Square brackets name the tool you call; angle brackets "
        "stand for what the tool or the facts return. Reply in the customer's "
        "language.",
    ]
    for exchange in shown:
        lines.extend(
            [
                f"{EXAMPLE_TITLES[exchange.kind]}:",
                f"Customer: {exchange.customer_line}",
                f"Assistant: {exchange.assistant_line}",
            ]
        )

    return lines
