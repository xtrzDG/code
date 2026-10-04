from enum import StrEnum


class CsvExportKind(StrEnum):
    """
    The tables an owner downloads as CSV (Excel, an accountant): the same
    lists the cabinet shows, with the same filters.
    """

    BOOKINGS = "bookings"
    LEADS = "leads"
    CONTACTS = "contacts"
    CONVERSATIONS = "conversations"
    AUDIT_LOG = "audit_log"


class BusinessExportStatus(StrEnum):
    """
    Where a full export of a business stands: QUEUED for the worker,
    RUNNING while it writes the archive, READY to download until it
    expires, EXPIRED once its archive was deleted, FAILED with the reason.
    """

    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    EXPIRED = "expired"
    FAILED = "failed"
