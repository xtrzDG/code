import logging
from collections.abc import Iterator

from typed_time_provider import Microseconds, Seconds, WallClock

from app.contracts.media_storage import MediaStorageAdapterContract
from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.contracts.repositories.media_repositories import MessageMediaRepoContract
from app.contracts.repositories.retention_repositories import (
    BusinessPrivacySettingsRepoContract,
    ExpiredLlmTurnRepoContract,
    ExpiredMessageRepoContract,
    ExpiredMissedCallRepoContract,
    ExpiringRecordRepoContract,
    QuietConversationRepoContract,
    RetentionPurgeStateRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.privacy import ProcessorErasureReason
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.retention_purges import (
    RetentionPurgeCounts,
    RetentionPurgeStateDocument,
)
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.dto.retention import RetentionWindow
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.compliance.retention.conversation_purge import (
    ConversationContentPurge,
    ConversationPurger,
    ModelRecordPurge,
)
from app.use_cases.compliance.retention.record_purge import (
    AnonymizedRecords,
    DeletedRecords,
    RecordPurger,
)
from app.use_cases.compliance.retention.retention_audit import (
    retention_audit_entries,
    window_since,
)
from app.use_cases.shared.business_walk import walk_businesses

LOGGER: logging.Logger = logging.getLogger(__name__)
SECONDS_PER_DAY: int = 24 * 60 * 60


class PurgeExpiredPersonalDataUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Daily retention job (`purge_expired_personal_data`): every business's
    customer data past the periods it chose in Settings → Privacy goes.

    - Conversations quiet for `llm_turn_retention_days` lose the records of
      their model calls, and their traces at Langfuse are deleted.
    - Messages (and the files customers sent) and missed calls older than
      `conversation_retention_days` are deleted; conversations quiet that
      long lose the team's notes and their calls' recordings, transcripts
      and numbers (and the calls at ElevenLabs); leads and handoffs made
      and bookings whose visit ended that long ago keep only what is not
      personal, as an erasure leaves them.

    Reads are indexed keyset batches of what went past retention since the
    previous run (the cutoffs in the business's purge state), deletes run
    in transactions of at most 1,000 rows, and the deletions at the
    sub-processors are queued jobs with retries. Each kind of record
    removed is audited as RETENTION_PURGE with its count. Running it again
    is harmless; a failing business does not stop the others (the run
    fails at the end, so it is tried again).
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        privacy_settings_repo: BusinessPrivacySettingsRepoContract,
        purge_state_repo: RetentionPurgeStateRepoContract,
        quiet_conversation_repo: QuietConversationRepoContract,
        llm_turn_repo: ExpiredLlmTurnRepoContract,
        note_repo: ConversationNoteRepoContract,
        call_repo: CallRepoContract,
        recording_storage: RecordingStorageAdapterContract,
        message_repo: ExpiredMessageRepoContract,
        message_media_repo: MessageMediaRepoContract,
        media_storage: MediaStorageAdapterContract,
        missed_call_repo: ExpiredMissedCallRepoContract,
        lead_repo: ExpiringRecordRepoContract[LeadDocument],
        booking_repo: ExpiringRecordRepoContract[BookingDocument],
        handoff_repo: ExpiringRecordRepoContract[HandoffDocument],
        processor_erasure: ProcessorErasureFacilitatorContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._privacy_settings_repo: BusinessPrivacySettingsRepoContract = (
            privacy_settings_repo
        )
        self._purge_state_repo: RetentionPurgeStateRepoContract = purge_state_repo
        self._conversations: ConversationPurger = ConversationPurger(
            quiet_conversation_repo,
            llm_turn_repo,
            note_repo,
            call_repo,
            recording_storage,
        )
        self._records: RecordPurger = RecordPurger(
            message_repo,
            message_media_repo,
            media_storage,
            missed_call_repo,
            lead_repo,
            booking_repo,
            handoff_repo,
        )
        self._processor_erasure: ProcessorErasureFacilitatorContract = processor_erasure
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        processed: int = 0
        failure: ApplicationError | None = None
        for business_id in self._business_ids():
            try:
                processed += self._purge(business_id)
            except ApplicationError as error:
                LOGGER.warning(
                    "Retention purge of %s failed: %s",
                    business_id,
                    type(error).__name__,
                )
                failure = failure or error

        if failure is not None:
            raise failure

        return JobReport(processed_count=ProcessedItemCount(processed))

    def _business_ids(self) -> Iterator[BusinessId]:
        # Every business, a keyset batch at a time (a job over the platform).
        for business in walk_businesses(self._business_repo):
            yield business.id

    def _purge(self, business_id: BusinessId) -> int:
        settings: BusinessPrivacySettingsDocument = (
            self._privacy_settings_repo.get_or_default(business_id)
        )
        state: RetentionPurgeStateDocument = self._purge_state_repo.get_or_new(
            business_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        llm_cutoff: Microseconds = self._cutoff(int(settings.llm_turn_retention_days))
        cutoff: Microseconds = self._cutoff(int(settings.conversation_retention_days))
        llm_window: RetentionWindow | None = window_since(
            state.llm_turns_purged_before, llm_cutoff
        )
        window: RetentionWindow | None = window_since(
            state.conversations_purged_before, cutoff
        )
        model = (
            ModelRecordPurge()
            if llm_window is None
            else self._conversations.purge_model_records(business_id, llm_window)
        )
        content = (
            ConversationContentPurge()
            if window is None
            else self._conversations.purge_content(business_id, window, now)
        )
        deleted: DeletedRecords = self._records.delete_before(business_id, cutoff)
        anonymized = (
            AnonymizedRecords(leads=0, bookings=0, handoffs=0)
            if window is None
            else self._records.anonymize_in(business_id, window, now)
        )
        self._processor_erasure.request_erasure(
            ProcessorErasureScope(
                business_id=business_id,
                reason=ProcessorErasureReason.RETENTION,
                conversation_ids=model.conversation_ids,
                provider_call_ids=content.provider_call_ids,
            )
        )
        counts = RetentionPurgeCounts(
            deleted_messages=ErasedRecordCount(deleted.messages),
            deleted_llm_turns=ErasedRecordCount(model.deleted_turns),
            deleted_notes=ErasedRecordCount(content.deleted_notes),
            deleted_media=ErasedRecordCount(deleted.media),
            deleted_missed_calls=ErasedRecordCount(deleted.missed_calls),
            erased_calls=ErasedRecordCount(content.erased_calls),
            anonymized_leads=ErasedRecordCount(anonymized.leads),
            anonymized_bookings=ErasedRecordCount(anonymized.bookings),
            anonymized_handoffs=ErasedRecordCount(anonymized.handoffs),
        )
        for entry in retention_audit_entries(business_id, counts, now):
            self._audit_log_repo.append(entry)

        state.llm_turns_purged_before = latest(
            state.llm_turns_purged_before, llm_cutoff
        )
        state.conversations_purged_before = latest(
            state.conversations_purged_before, cutoff
        )
        state.last_run_at = now
        state.last_counts = counts
        state.updated_at = now
        self._purge_state_repo.save(state)
        return sum(int(getattr(counts, name)) for name in type(counts).model_fields)

    def _cutoff(self, days: int) -> Microseconds:
        return self._wall_clock.now_unix_with_delta(Seconds(-days * SECONDS_PER_DAY))


def latest(previous: Microseconds | None, cutoff: Microseconds) -> Microseconds:
    """A cutoff never moves back: a longer period keeps what is gone, gone."""

    if previous is None or int(cutoff) > int(previous):
        return cutoff

    return previous
