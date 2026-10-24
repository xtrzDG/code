from enum import StrEnum


class CallForwardingCondition(StrEnum):
    """
    When a carrier forwards a call to the assistant (GSM conditional forwarding).

    The concept forwards only "no answer / busy / unreachable", never every
    call, so staff still answer first. CANCEL_ALL switches forwarding off.
    """

    NO_ANSWER = "no_answer"
    BUSY = "busy"
    UNREACHABLE = "unreachable"
    CANCEL_ALL = "cancel_all"


class CabinetLanguage(StrEnum):
    """
    The languages the owner cabinet is translated into, in the order of the
    cabinet's language list (`web/src/i18n/config.ts`). Every owner-facing
    catalog text exists in each of them; English is the only fallback.
    """

    GEORGIAN = "ka"
    RUSSIAN = "ru"
    ENGLISH = "en"
    HEBREW = "he"
    GERMAN = "de"


CABINET_LANGUAGES: tuple[CabinetLanguage, ...] = tuple(CabinetLanguage)


class CountryOnboardingStatus(StrEnum):
    """Whether businesses from a country may create an assistant."""

    SUPPORTED = "supported"
    PILOT = "pilot"
    RESTRICTED = "restricted"


class DataRegion(StrEnum):
    """Region where customer conversations and personal data are processed."""

    EU = "eu"
    US = "us"


class LanguageTextSupport(StrEnum):
    """How well the assistant handles a language in text channels."""

    SUPPORTED = "supported"
    BETA = "beta"


class LanguageVoiceSupport(StrEnum):
    """How well the assistant handles a language on phone calls."""

    VERIFIED = "verified"
    BETA = "beta"
    NEEDS_PILOT_CHECK = "needs_pilot_check"
    UNSUPPORTED = "unsupported"


class LocalNumberProvisioning(StrEnum):
    """Whether an assistant phone number can be bought inside the country."""

    AVAILABLE = "available"
    REQUIRES_DOCUMENTS = "requires_documents"
    UNAVAILABLE = "unavailable"


class OtpDeliveryChannel(StrEnum):
    """Channel used to deliver one-time login codes."""

    SMS = "sms"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    EMAIL = "email"


class PhoneNumberKind(StrEnum):
    """Phone number line type reported by the numbering plan."""

    MOBILE = "mobile"
    FIXED_LINE = "fixed_line"
    FIXED_LINE_OR_MOBILE = "fixed_line_or_mobile"
    TOLL_FREE = "toll_free"
    VOIP = "voip"
    OTHER = "other"


class RecordingConsentRule(StrEnum):
    """What the law requires before a call may be recorded."""

    NOTICE = "notice"
    ALL_PARTY_CONSENT = "all_party_consent"


class TextDirection(StrEnum):
    """Writing direction of a language script."""

    LEFT_TO_RIGHT = "ltr"
    RIGHT_TO_LEFT = "rtl"


class TextReviewStatus(StrEnum):
    """
    Whether a translation of the owner text catalog was checked by a native
    speaker (REVIEWED) or is a draft that still waits for that check
    (NEEDS_REVIEW, shown to owners all the same, English being worse).
    """

    REVIEWED = "reviewed"
    NEEDS_REVIEW = "needs_review"
