from enum import StrEnum


class LegalDocumentKind(StrEnum):
    """
    The platform's own public texts (docs/legal): the terms of service, the
    privacy policy, the cookie statement and the security overview of the
    public /security page. The data processing agreement has its own
    versions and acceptance (DPA_*).
    """

    TERMS = "terms"
    PRIVACY = "privacy"
    COOKIES = "cookies"
    SECURITY = "security"


class SubprocessorChangeKind(StrEnum):
    """What a change of the sub-processor list does (DPA section 8.3)."""

    ADDED = "added"
    REMOVED = "removed"
