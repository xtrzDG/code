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
    autotest run.
    """

    TEST_CHAT = "test_chat"
    MENU_IMPORT = "menu_import"
    AUTOTEST_RUN = "autotest_run"


class RequestLimitClass(StrEnum):
    """
    Which generic request limit a signed-in request counts against: every
    request (GENERAL) or, stricter, a data export (EXPORT).
    """

    GENERAL = "general"
    EXPORT = "export"
