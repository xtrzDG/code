"""What Meta says about a business's WhatsApp templates."""

from enum import StrEnum


class WhatsAppTemplateCategory(StrEnum):
    """
    Meta's category of a WhatsApp template, which decides what it may say
    and what it costs. Service messages the platform sends (text-backs,
    reminders, confirmations, staff replies) go as UTILITY; MARKETING may
    promote and reaches only customers who gave marketing consent.
    """

    MARKETING = "marketing"
    UTILITY = "utility"
    AUTHENTICATION = "authentication"
