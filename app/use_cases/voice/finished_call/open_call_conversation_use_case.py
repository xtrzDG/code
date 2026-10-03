"""Every call the caller spoke in gets a conversation (its card shows the call)."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channel_events import PostCallEventStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import CallDocument, ConversationDocument
from app.schemas.dto.calls.missed_calls import StoredFinishedCall
from app.schemas.dto.voice_webhooks import RecordedCall
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class OpenCallConversationUseCase(UseCaseContract[StoredFinishedCall, RecordedCall]):
    """
    A call the caller spoke in but where the phone assistant used no tool
    has no conversation yet, so staff could not find it, its recording or
    its summary. It gets one now: a phone conversation of the caller (the
    contact whose phone the call proved, else a new one) pinned to the
    live version, and the call points to it. Calls with a conversation,
    calls nobody spoke in, abandoned calls and calls of a business without
    a live version stay as they are.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        call_repo: CallRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._call_repo: CallRepoContract = call_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: StoredFinishedCall) -> RecordedCall:
        recorded: RecordedCall = input_data.call
        if (
            recorded.status is PostCallEventStatus.IGNORED
            or recorded.business_id is None
            or recorded.call_id is None
            or recorded.conversation_id is not None
            or recorded.outcome is CallOutcome.ABANDONED
            or not any(
                line.author is MessageAuthor.CUSTOMER
                for line in input_data.report.transcript
            )
        ):
            return recorded

        business: BusinessDocument | None = self._business_repo.get(
            recorded.business_id
        )
        call: CallDocument | None = self._call_repo.get(
            recorded.business_id, recorded.call_id
        )
        if (
            business is None
            or call is None
            or business.published_assistant_version_id is None
        ):
            return recorded

        now: Microseconds = self._wall_clock.now_unix()
        contact: ContactDocument = self._resolve_caller(business, call, now)
        conversation = ConversationDocument(
            business_id=business.id,
            contact_id=contact.id,
            assistant_version_id=business.published_assistant_version_id,
            channel=ChannelKind.PHONE,
            channel_user_id=ChannelUserId(str(call.provider_call_id)),
            language=recorded.language,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        self._conversation_repo.save(conversation)

        def point_to_conversation(current: CallDocument) -> CallDocument | None:
            if current.conversation_id is not None:
                return None

            current.conversation_id = conversation.id
            current.updated_at = now
            return current

        self._call_repo.update(business.id, call.id, point_to_conversation)
        self._live_events.publish(
            business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation.id,)
        )
        return recorded.model_copy(
            update={"conversation_id": conversation.id, "contact_id": contact.id}
        )

    def _resolve_caller(
        self,
        business: BusinessDocument,
        call: CallDocument,
        now: Microseconds,
    ) -> ContactDocument:
        caller: E164PhoneNumber | None = call.from_phone_number
        identity = ChannelIdentity(
            channel=ChannelKind.PHONE,
            channel_user_id=ChannelUserId(
                str(call.provider_call_id) if caller is None else str(caller)
            ),
        )
        contact: ContactDocument | None = (
            None
            if caller is None
            else self._contact_repo.find_by_verified_phone_number(business.id, caller)
        ) or self._contact_repo.find_by_channel_identity(
            business.id, identity.channel, identity.channel_user_id
        )
        if contact is not None:
            return contact

        contact = ContactDocument(
            business_id=business.id,
            phone_number=caller,
            verified_phone_number=caller,
            channel_identities=[identity],
            created_at=now,
            updated_at=now,
        )
        self._contact_repo.save(contact)
        return contact
