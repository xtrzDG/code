"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class ConversationRetentionDays(BaseConstrainedTypedInt):
    """
    Days a business keeps its customers' conversations (messages, the
    team's notes, call transcripts) after their last message; then the
    retention purge deletes them and anonymizes the leads, bookings and
    handoffs they produced. At least 30 days (the hosted privacy notice and
    the DPA promise the business's own choice), at most ten years.
    """

    ge = 30
    le = 3650


class ExportArchiveByteCount(BaseConstrainedTypedInt):
    """Size of a business's export archive (the ZIP), in bytes."""

    ge = 0


class ExportArchiveLifetimeHours(BaseConstrainedTypedInt):
    """How long a written export archive is kept before it is deleted, in hours."""

    ge = 1
    le = 168


class ExportDownloadCount(BaseConstrainedTypedInt):
    """How many times a full business export was downloaded (at most 3)."""

    ge = 0


class ExportDownloadLinkMinutes(BaseConstrainedTypedInt):
    """
    How long a one-time download link of a full business export works, in
    minutes (EXPORT_DOWNLOAD_LINK_MINUTES; DPA section 9 promises 10 at
    most).
    """

    ge = 1
    le = 10


class ExportedRecordCount(BaseConstrainedTypedInt):
    """How many records (rows, documents) one export wrote."""

    ge = 0


class LlmTurnRetentionDays(BaseConstrainedTypedInt):
    """
    Days the records of a conversation's model calls (the verbatim model
    transcript and its traces at the quality journal) are kept after the
    conversation's last message. At most 30, the period the DPA promises.
    """

    ge = 1
    le = 30


class ProcessorErasureJobCount(BaseConstrainedTypedInt):
    """
    How many deletion jobs were queued for the sub-processors (one per
    processor and batch of up to 100 conversations or calls).
    """

    ge = 0


class RetentionBatchSize(BaseConstrainedTypedInt):
    """
    How many records the retention purge reads in one keyset batch (the
    deletes themselves go in transactions of at most 1,000 rows).
    """

    ge = 1
    le = 1000


class SuppressedIdentityCount(BaseConstrainedTypedInt):
    """How many identities (numbers, channel accounts) a suppression covers."""

    ge = 0


# Keep abc order for all non example types, if possible.
