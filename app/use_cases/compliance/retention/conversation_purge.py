"""
The retention purge of what hangs on a business's conversations: the
records of model calls of conversations quiet for the model-record
period, and the team's notes, the calls and the customer memory's summary
of conversations quiet for the conversation period.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.contracts.repositories.conversation_repositories import CallRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.contracts.repositories.retention_repositories import (
    ExpiredLlmTurnRepoContract,
    QuietConversationRepoContract,
)
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.call_recordings import RecordingLocation
from app.schemas.dto.retention import RetentionWindow
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.use_cases.compliance.record_anonymization import erased_call
from app.use_cases.compliance.retention.retention_walk import (
    RETENTION_BATCH_SIZE,
    walk_batches,
)
from app.utilities.channels.voice_recordings import read_voice_platform_call_id


@dataclass
class ModelRecordPurge:
    """The model turns deleted, and the conversations they belonged to."""

    deleted_turns: int = 0
    conversation_ids: list[ConversationId] = field(default_factory=list[ConversationId])


@dataclass
class ConversationContentPurge:
    """The notes deleted, the calls erased, and every call's platform id."""

    deleted_notes: int = 0
    erased_calls: int = 0
    provider_call_ids: list[ProviderCallId] = field(
        default_factory=list[ProviderCallId]
    )


@dataclass(frozen=True)
class ConversationPurger:
    quiet_conversation_repo: QuietConversationRepoContract
    llm_turn_repo: ExpiredLlmTurnRepoContract
    note_repo: ConversationNoteRepoContract
    call_repo: CallRepoContract
    recording_storage: RecordingStorageAdapterContract

    def purge_model_records(
        self, business_id: BusinessId, window: RetentionWindow
    ) -> ModelRecordPurge:
        """Delete the model transcripts of the conversations in `window`."""

        purge = ModelRecordPurge()
        for conversation in self._quiet(business_id, window):
            deleted: int = int(
                self.llm_turn_repo.delete_by_conversation(conversation.id)
            )
            if deleted > 0:
                purge.deleted_turns += deleted
                purge.conversation_ids.append(conversation.id)

        return purge

    def purge_content(
        self, business_id: BusinessId, window: RetentionWindow, now: Microseconds
    ) -> ConversationContentPurge:
        """
        Delete the notes of the conversations in `window`, forget what the
        customer memory summarized of them and erase their calls: an
        archived recording is deleted from storage here, one the voice
        platform still keeps goes with its conversation there (a queued
        deletion of every call's `provider_call_id`).
        """

        purge = ConversationContentPurge()
        for conversation in self._quiet(business_id, window):
            if conversation.summary is not None:
                self.quiet_conversation_repo.change(
                    conversation, lambda stored: without_summary(stored, now)
                )
            purge.deleted_notes += int(
                self.note_repo.delete_by_conversation(business_id, conversation.id)
            )
            for call in self.call_repo.list_by_conversation(
                business_id, conversation.id
            ):
                purge.provider_call_ids.append(call.provider_call_id)
                if self._erase_call(call, now):
                    purge.erased_calls += 1

        return purge

    def _quiet(
        self, business_id: BusinessId, window: RetentionWindow
    ) -> Iterator[ConversationDocument]:
        return walk_batches(
            lambda after: self.quiet_conversation_repo.page_quiet_in(
                business_id, window, after, RETENTION_BATCH_SIZE
            )
        )

    def _erase_call(self, call: CallDocument, now: Microseconds) -> bool:
        if (
            call.recording_path is not None
            and read_voice_platform_call_id(call.recording_path) is None
        ):
            self.recording_storage.delete(
                RecordingLocation(
                    business_id=call.business_id, path=call.recording_path
                )
            )

        erased: CallDocument | None = self.call_repo.update(
            call.business_id, call.id, lambda stored: erased_call(stored, now)
        )
        return erased is not None


def without_summary(
    conversation: ConversationDocument, now: Microseconds
) -> ConversationDocument | None:
    """The conversation without its summary; None when it has none left."""

    if conversation.summary is None and conversation.summarized_at is None:
        return None

    return conversation.model_copy(
        update={"summary": None, "summarized_at": None, "updated_at": now}
    )
