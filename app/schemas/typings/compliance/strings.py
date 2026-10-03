"""Keep abc order."""

from base_typed_string import BaseTypedString


class AuditEntityName(BaseTypedString):
    """Name of the audited entity type, e.g. "booking"."""


class AuditEntityReference(BaseTypedString):
    """Identifier of the audited entity as text (any id type)."""


class ClientIpAddress(BaseTypedString):
    """IP address of the caller as reported by the transport."""


class LegalDocumentMarkdown(BaseTypedString):
    """Full text of a legal document (e.g. the DPA) in Markdown."""


class LegalDocumentTitle(BaseTypedString):
    """Heading of a legal document in its language."""


# Keep abc order for all non example types, if possible.
