"""
The retention purge of a business's own records past the conversation
period: messages (and the files customers sent with them) and missed
calls are deleted by indexed range deletes, leads, handoffs and bookings
keep only what is not personal, as an erasure leaves them.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.repositories.retention_repositories import (
    ExpiredMessageRepoContract,
    ExpiredMissedCallRepoContract,
    ExpiringRecordRepoContract,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.media import MediaLocation
from app.schemas.dto.retention import RetentionWindow
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.use_cases.compliance.record_anonymization import (
    EXPIRED_TEXT,
    anonymized_booking,
    anonymized_handoff,
    anonymized_lead,
)
from app.use_cases.compliance.retention.retention_walk import (
    RETENTION_BATCH_SIZE,
    walk_batches,
)


@dataclass(frozen=True)
class DeletedRecords:
    messages: int
    media: int
    missed_calls: int


@dataclass(frozen=True)
class AnonymizedRecords:
    leads: int
    bookings: int
    handoffs: int


@dataclass(frozen=True)
class RecordPurger:
    message_repo: ExpiredMessageRepoContract
    message_media_repo: MessageMediaRepoContract
    media_storage: MediaStorageAdapterContract
    missed_call_repo: ExpiredMissedCallRepoContract
    lead_repo: ExpiringRecordRepoContract[LeadDocument]
    booking_repo: ExpiringRecordRepoContract[BookingDocument]
    handoff_repo: ExpiringRecordRepoContract[HandoffDocument]

    def delete_before(
        self, business_id: BusinessId, cutoff: Microseconds
    ) -> DeletedRecords:
        """
        Delete what was written before `cutoff`: the customers' files first
        (a storage failure leaves their rows for the next run), then the
        messages and missed calls in transactions of at most 1,000 rows.
        """

        media = self.message_media_repo.list_created_before(business_id, cutoff)
        for item in media:
            self.media_storage.delete(
                MediaLocation(business_id=business_id, path=item.storage_path)
            )
            self.message_media_repo.delete(business_id, item.id)

        return DeletedRecords(
            messages=int(self.message_repo.delete_created_before(business_id, cutoff)),
            media=len(media),
            missed_calls=int(
                self.missed_call_repo.delete_created_before(business_id, cutoff)
            ),
        )

    def anonymize_in(
        self, business_id: BusinessId, window: RetentionWindow, now: Microseconds
    ) -> AnonymizedRecords:
        """
        Anonymize the leads and handoffs made in `window` and the bookings
        whose visit ended in it (never an upcoming visit's notes).
        """

        leads: int = 0
        for lead in walk_batches(
            lambda after: self.lead_repo.page_in(
                business_id, window, after, RETENTION_BATCH_SIZE
            )
        ):
            changed = self.lead_repo.change(
                lead, lambda stored: anonymized_lead(stored, EXPIRED_TEXT, now)
            )
            leads += changed is not None

        bookings: int = 0
        for booking in walk_batches(
            lambda after: self.booking_repo.page_in(
                business_id, window, after, RETENTION_BATCH_SIZE
            )
        ):
            changed_booking = self.booking_repo.change(
                booking, lambda stored: anonymized_booking(stored, now)
            )
            bookings += changed_booking is not None

        handoffs: int = 0
        for handoff in walk_batches(
            lambda after: self.handoff_repo.page_in(
                business_id, window, after, RETENTION_BATCH_SIZE
            )
        ):
            changed_handoff = self.handoff_repo.change(
                handoff,
                lambda stored: anonymized_handoff(stored, EXPIRED_TEXT, None, now),
            )
            handoffs += changed_handoff is not None

        return AnonymizedRecords(leads=leads, bookings=bookings, handoffs=handoffs)
