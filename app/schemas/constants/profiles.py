from enum import StrEnum


class ProfileGapKind(StrEnum):
    """One kind of item on the owner's "what to add" list (concept section 4)."""

    MISSING_REQUIRED_ANSWER = "missing_required_answer"
    NO_OPENING_HOURS = "no_opening_hours"
    NO_ADDRESS = "no_address"
    NO_HANDOFF_CONTACT = "no_handoff_contact"
    NO_BOOKING_RULES = "no_booking_rules"
    NO_RESOURCES = "no_resources"
    NO_PRICED_ITEMS = "no_priced_items"
    NO_FAQ = "no_faq"
    UNANSWERED_QUESTION = "unanswered_question"
