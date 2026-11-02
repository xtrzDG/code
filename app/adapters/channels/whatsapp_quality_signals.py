"""
Meta's warnings about a business's WhatsApp number or templates, reported
as the platform signal the WHATSAPP_QUALITY alert reads.
"""

import logging

from app.contracts.monitoring import SignalCounterAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.utilities.channels.json_values import JsonObject
from app.utilities.channels.whatsapp_webhook_parts import quality_warnings

LOGGER: logging.Logger = logging.getLogger(__name__)


def report_quality_warnings(
    change: JsonObject, signal_counter: SignalCounterAdapterContract | None
) -> None:
    """
    One log line for the warnings of a webhook change (the number flagged
    or downgraded, a template's quality down, a template paused, disabled
    or moved into the marketing category) and one WHATSAPP_QUALITY_DROP
    signal each; nothing for any other change.
    """

    warnings: list[str] = quality_warnings(change)
    if not warnings:
        return

    LOGGER.warning("WhatsApp quality warning: %s.", "; ".join(warnings))
    if signal_counter is not None:
        for _ in warnings:
            signal_counter.count(PlatformSignal.WHATSAPP_QUALITY_DROP)
