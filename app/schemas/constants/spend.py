from enum import StrEnum


class SpendLevel(StrEnum):
    """
    Where one business's provider spend of its day stands against its
    limits: under both (NORMAL), past the soft limit (its assistant answers
    on a cheaper model; the owner and the platform team are told once), or
    past the hard limit (the assistant only takes messages for the team
    until the day ends; told once, and audited).
    """

    NORMAL = "normal"
    SOFT_LIMIT = "soft_limit"
    HARD_LIMIT = "hard_limit"


class PlatformBrake(StrEnum):
    """
    Why every business's assistant holds the language model back at once,
    whatever its own spend: a platform admin paused them all (PAUSED), or
    the platform's provider spend of the UTC day reached the share of its
    daily budget where it stops (BUDGET_STOP). Customers are handed to
    the team in their language and calls go to the forwarding number.
    """

    PAUSED = "paused"
    BUDGET_STOP = "budget_stop"


class SpendProvider(StrEnum):
    """
    Who the platform pays for a kind of metered usage: the language model
    (OpenAI or Anthropic tokens), the voice agent (ElevenLabs minutes), the
    telephony of a transferred call, WhatsApp templates (Meta) and the
    transcription of voice notes.
    """

    LANGUAGE_MODEL = "language_model"
    VOICE = "voice"
    TELEPHONY = "telephony"
    WHATSAPP = "whatsapp"
    TRANSCRIPTION = "transcription"


class OwnerAction(StrEnum):
    """
    A cabinet action that makes the platform pay a provider and is limited
    per person or per business: a test chat message, a menu import, an
    autotest run, a request for an item's aliases in other languages, a
    search of the carrier's numbers, a number rented and a request for a
    number (it e-mails the platform team).
    """

    TEST_CHAT = "test_chat"
    MENU_IMPORT = "menu_import"
    AUTOTEST_RUN = "autotest_run"
    ALIAS_SUGGESTION = "alias_suggestion"
    PHONE_NUMBER_SEARCH = "phone_number_search"
    PHONE_NUMBER_RENTAL = "phone_number_rental"
    PHONE_NUMBER_REQUEST = "phone_number_request"


class RequestLimitClass(StrEnum):
    """
    Which generic request limit a signed-in request counts against: every
    request (GENERAL) or, stricter, a data export (EXPORT).
    """

    GENERAL = "general"
    EXPORT = "export"
