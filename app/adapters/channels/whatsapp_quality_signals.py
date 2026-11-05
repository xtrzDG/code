"""
Meta's warnings about a business's WhatsApp number or templates, reported
as the platform signal the WHATSAPP_QUALITY alert reads.
"""

import logging

from app.contracts.monitoring import SignalCounterAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.utilities.channels.json_values import JsonObject, read_text
from app.utilities.channels.whatsapp_webhook_parts import quality_warnings

LOGGER: logging.Logger = logging.getLogger(__name__)
# Meta's WhatsApp Business Account ids are digits; anything else is not
# logged as one.
MAX_ACCOUNT_ID_LENGTH: int = 32
UNKNOWN_ACCOUNT: str = "unknown"


def report_quality_warnings(
    entry: JsonObject,
    change: JsonObject,
    signal_counter: SignalCounterAdapterContract | None,
) -> None:
    """
    One log line for the warnings of a webhook change (the number flagged
    or downgraded, a template's quality down, a template paused, disabled
    or moved into the marketing category), naming the WhatsApp Business
    Account of the entry (the channel's `whatsapp_business_account_id`)
    so the platform team finds the business, and one WHATSAPP_QUALITY_DROP
    signal each; nothing for any other change.
    """

    warnings: list[str] = quality_warnings(change)
    if not warnings:
        return

    LOGGER.warning(
        "WhatsApp quality warning of business account %s: %s.",
        business_account_label(entry),
        "; ".join(warnings),
    )
    if signal_counter is not None:
        for _ in warnings:
            signal_counter.count(PlatformSignal.WHATSAPP_QUALITY_DROP)


def business_account_label(entry: JsonObject) -> str:
    """The entry's account id as Meta sent it when it is one, else unknown."""

    account: str = read_text(entry, "id") or ""
    if account.isdigit() and len(account) <= MAX_ACCOUNT_ID_LENGTH:
        return account

    return UNKNOWN_ACCOUNT
