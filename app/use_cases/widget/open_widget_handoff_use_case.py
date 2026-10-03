from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.repositories.business_repositories import (
    BusinessRepoContract,
    ChannelRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_handoff import (
    WidgetHandoffCommand,
    WidgetHandoffTarget,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.conversations.turns.conversation_resolution import (
    find_open_conversation,
)
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.widget_handoff_texts import (
    LAST_MESSAGE,
    PERSON_REQUESTED,
    quote_last_message,
)
from app.utilities.channels.widget_rate_limits import (
    WIDGET_HANDOFF_LIMITS,
    refuse_too_frequent_widget_requests,
)


class OpenWidgetHandoffUseCase(
    UseCaseContract[WidgetHandoffCommand, WidgetHandoffTarget]
):
    """
    Find the conversation a website visitor's "Talk to a person" goes to:
    the one their next message would land in (staff's, however old, else
    one with a message in the last 24 hours), or a new one when they have
    not written yet, so they can ask for a person before typing anything.

    The chat must be switched on and the assistant live (else the chat is
    unavailable, as for messages). Requests are limited per visitor, per
    network, per business and for the platform (they notify staff). The
    staff summary says what happened and quotes the visitor's last message,
    in the business's staff language.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        channel_repo: ChannelRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        text_resolver: LocalizedTextResolverContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._text_resolver: LocalizedTextResolverContract = text_resolver
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetHandoffCommand) -> WidgetHandoffTarget:
        now: Microseconds = self._wall_clock.now_unix()
        refuse_too_frequent_widget_requests(
            self._rate_limit_registry,
            WIDGET_HANDOFF_LIMITS,
            business_id=input_data.business_id,
            session_key=input_data.request.session_key,
            client_ip_address=input_data.client_ip_address,
            now=now,
        )
        business: BusinessDocument = self._require_open_chat(input_data)
        visitor = ChannelUserId(str(input_data.request.session_key))
        contact: ContactDocument = self._find_or_add_contact(business, visitor, now)
        conversation: ConversationDocument = find_open_conversation(
            self._conversation_repo,
            business,
            contact,
            ChannelKind.WEB_CHAT,
            False,
            now,
        ) or self._start_conversation(business, contact, visitor, now)
        language: LanguageTag = (
            conversation.language
            or input_data.request.language
            or business.default_language
        )
        return WidgetHandoffTarget(
            business_id=business.id,
            conversation_id=conversation.id,
            contact_id=contact.id,
            language=language,
            summary=self._summary(business, conversation),
            is_already_handed_off=conversation.status is ConversationStatus.HANDOFF,
        )

    def _require_open_chat(self, input_data: WidgetHandoffCommand) -> BusinessDocument:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        channel: ChannelDocument | None = (
            None
            if business is None
            else find_business_channel(
                self._channel_repo, business.id, ChannelKind.WEB_CHAT
            )
        )
        if (
            business is None
            or channel is None
            or channel.status is not ChannelStatus.CONNECTED
        ):
            raise NotFoundError("This chat is not available.")

        if (
            business.status is not BusinessStatus.LIVE
            or business.published_assistant_version_id is None
        ):
            raise ConflictError(f"The assistant of {business.name} is not live.")

        return business

    def _find_or_add_contact(
        self,
        business: BusinessDocument,
        visitor: ChannelUserId,
        now: Microseconds,
    ) -> ContactDocument:
        contact: ContactDocument | None = self._contact_repo.find_by_channel_identity(
            business.id, ChannelKind.WEB_CHAT, visitor
        )
        if contact is not None:
            return contact

        contact = ContactDocument(
            business_id=business.id,
            channel_identities=[
                ChannelIdentity(channel=ChannelKind.WEB_CHAT, channel_user_id=visitor)
            ],
            created_at=now,
            updated_at=now,
        )
        self._contact_repo.save(contact)
        return contact

    def _start_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        visitor: ChannelUserId,
        now: Microseconds,
    ) -> ConversationDocument:
        if business.published_assistant_version_id is None:
            raise ConflictError(f"The assistant of {business.name} is not live.")

        conversation = ConversationDocument(
            business_id=business.id,
            contact_id=contact.id,
            assistant_version_id=business.published_assistant_version_id,
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=visitor,
            last_message_at=now,
            created_at=now,
            updated_at=now,
        )
        self._conversation_repo.save(conversation)
        return conversation

    def _summary(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
    ) -> HandoffSummary:
        language: LanguageTag = business.owner_language
        lines: list[str] = [
            str(self._text_resolver.resolve(PERSON_REQUESTED, language))
        ]
        last_question: MessageDocument | None = next(
            (
                message
                for message in reversed(
                    self._message_repo.list_by_conversation(
                        business.id, conversation.id
                    )
                )
                if message.author is MessageAuthor.CUSTOMER
            ),
            None,
        )
        if last_question is not None:
            lines.append(
                str(self._text_resolver.resolve(LAST_MESSAGE, language)).replace(
                    "{message}", quote_last_message(str(last_question.text))
                )
            )

        return HandoffSummary(" ".join(lines))
