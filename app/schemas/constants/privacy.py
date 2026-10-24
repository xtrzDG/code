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


class SubProcessor(StrEnum):
    """
    The sub-processors that may keep copies of a business's customer data
    outside the platform's own database and storage, and so are asked to
    delete them when the platform deletes its own (an erasure, the
    retention purge): Langfuse (traces of model calls), ElevenLabs (call
    audio and transcripts), and Meta and Telegram, whose copies are the
    customer's own chat and cannot be deleted by the business (see
    `messaging_platform_erasure_adapter`).
    """

    LANGFUSE = "langfuse"
    ELEVENLABS = "elevenlabs"
    META = "meta"
    TELEGRAM = "telegram"


class ProcessorErasureReason(StrEnum):
    """Why copies at a sub-processor are deleted: an erasure or retention."""

    CONTACT_ERASURE = "contact_erasure"
    RETENTION = "retention"
