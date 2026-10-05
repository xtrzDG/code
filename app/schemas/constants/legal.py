from enum import StrEnum


class LegalDocumentKind(StrEnum):
    """
    The platform's own legal texts for business owners (docs/legal): the
    terms of service, the privacy policy and the cookie statement. The data
    processing agreement has its own versions and acceptance (DPA_*).
    """

    TERMS = "terms"
    PRIVACY = "privacy"
    COOKIES = "cookies"


class SubprocessorChangeKind(StrEnum):
    """What a change of the sub-processor list does (DPA section 8.3)."""

    ADDED = "added"
    REMOVED = "removed"
