from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.privacy.prefixed_id import RetentionPurgeStateId

NO_RECORDS: ErasedRecordCount = ErasedRecordCount(0)


class RetentionPurgeCounts(PersistentDocument):
    """What one run of a business's retention purge deleted or anonymized."""

    deleted_messages: ErasedRecordCount = NO_RECORDS
    deleted_llm_turns: ErasedRecordCount = NO_RECORDS
    deleted_notes: ErasedRecordCount = NO_RECORDS
    deleted_media: ErasedRecordCount = NO_RECORDS
    deleted_missed_calls: ErasedRecordCount = NO_RECORDS
    erased_calls: ErasedRecordCount = NO_RECORDS
    anonymized_leads: ErasedRecordCount = NO_RECORDS
    anonymized_bookings: ErasedRecordCount = NO_RECORDS
    anonymized_handoffs: ErasedRecordCount = NO_RECORDS


class RetentionPurgeStateDocument(BaseDocument):
    """
    How far the retention purge of one business got (one document per
    business, the id derived from it; written by the purge only, never by
    the owner's settings, so neither overwrites the other).

    `conversations_purged_before` and `llm_turns_purged_before` are the
    cutoffs of the last finished run: conversations whose last message
    came before them were purged, so the next run reads only the
    conversations that went quiet since (an indexed range of
    `last_message_at`). None until a first run finished. `last_run_at` and
    `last_counts` are what Settings → Privacy shows.
    """

    id: RetentionPurgeStateId
    business_id: BusinessId
    conversations_purged_before: Microseconds | None = None
    llm_turns_purged_before: Microseconds | None = None
    last_run_at: Microseconds | None = None
    last_counts: RetentionPurgeCounts = Field(default_factory=RetentionPurgeCounts)
