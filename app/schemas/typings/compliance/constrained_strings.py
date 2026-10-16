"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AuditChainKey(BaseConstrainedTypedString):
    """
    Which hash chain of the audit log an entry belongs to: a business's
    own log (its business id) or the platform's (`platform`, the entries
    that name no business).

    Example:
        chain = AuditChainKey("platform")
    """

    min_length = 8
    max_length = 80
    pattern = r"^(platform|business_[0-9A-Za-z-]{1,70})$"


class AuditEntryHash(BaseConstrainedTypedString):
    """
    SHA-256 of an audit entry's canonical JSON (with the hash of the entry
    before it in its chain), 64 lowercase hex digits.

    Example:
        entry_hash = AuditEntryHash("0" * 64)
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class DpaAcceptanceDueDate(BaseConstrainedTypedString):
    """
    The day by which owners accept a new agreement version, ISO 8601
    "YYYY-MM-DD": 30 days after the version's date (DPA 15.2).

    Example:
        due_on = DpaAcceptanceDueDate("2026-11-05")
    """

    min_length = 10
    max_length = 10
    pattern = r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class DpaDocumentVersion(BaseConstrainedTypedString):
    """
    Version of the data processing agreement text, e.g. "2026-10-01".

    Example:
        version = DpaDocumentVersion("2026-10-01")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[0-9A-Za-z][0-9A-Za-z.\-_]*$"


class DpaDocumentUrl(BaseConstrainedTypedString):
    """
    API path that serves the text of one agreement version (GET, JSON with
    Markdown; `?language=` picks the translation).

    Example:
        url = DpaDocumentUrl("/v1/legal/dpa/2026-10-01")
    """

    min_length = 2
    max_length = 200
    pattern = r"^/v1/legal/dpa/[0-9A-Za-z][0-9A-Za-z.\-_]*$"


# Keep abc order for all non example types, if possible.
