from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import (
    MessageAuthor,
    StaffMessageDelivery,
    StaffReplyBlock,
)
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_actions import (
    SendStaffMessageCommand,
    StaffMessageResult,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    MessageView,
    StaffReplyView,
)
from app.schemas.dto.staff_reply_templates import StaffReplyTemplateView
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.conversations.staff_reply_deliveries import with_staff_deliveries
from app.use_cases.conversations.staff_reply_outbox import (
    StaffReplyOutbox,
    template_reply_text,
)
from app.use_cases.conversations.staff_reply_support import (
    assess_conversation_reply,
)
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.use_cases.shared.storage_transaction import in_unit_of_work
from app.utilities.channels.widget_live_signals import announce_widget_reply
from app.utilities.conversations.staff_replies import describe_block

MESSAGE_ENTITY: AuditEntityName = AuditEntityName("message")


class SendStaffMessageUseCase(
    UseCaseContract[SendStaffMessageCommand, StaffMessageResult]
):
    """
    An owner or staff member writes to the customer of a conversation from
    the cabinet (concept section 6: after a handoff a person answers in the
    same channel).

    Telegram, WhatsApp, Instagram and Messenger messages go into the outbox
    together with the transcript message, in one storage transaction, and
    the worker sends them through the business's connected channel with
    retries (`delivery` on the message says how it goes: sending, retrying,
    failed with its reason, delivered); WhatsApp, Instagram and Messenger
    only within 24 hours of the customer's last message there. After that,
    a WhatsApp message asked to go `as_template` travels in the message
    template the owner set for staff replies, in its approved language, as
    its single body parameter: one line (line breaks become spaces) of at
    most 1024 characters, else ValidationFailedError; a template Meta
    refuses fails with the reason `template_rejected`. Website chat
    messages are kept for the visitor's widget. Phone and test
    conversations cannot be written to; every refusal is a ConflictError
    that says why. The message is stored in the transcript as a STAFF
    message with its author, the conversation moves up the feed, the
    assistant is not asked to answer, and the message (personal data) is
    written to the audit log.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        channel_repo: ChannelRepoContract,
        audit_log_repo: AuditLogRepoContract,
        outbound_message_repo: OutboundMessageRepoContract,
        job_queue: JobQueueFacilitatorContract,
        message_transformer: TransformerContract[MessageDocument, MessageView],
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._outbox: StaffReplyOutbox = StaffReplyOutbox(channel_repo)
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work
        self._message_transformer: TransformerContract[MessageDocument, MessageView] = (
            message_transformer
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: SendStaffMessageCommand) -> StaffMessageResult:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        conversation: ConversationDocument = self._require_conversation(
            business, input_data
        )
        now: Microseconds = self._wall_clock.now_unix()
        reply: StaffReplyView = assess_conversation_reply(
            conversation,
            self._conversation_repo,
            self._message_repo,
            self._channel_repo,
            business.default_language,
            now,
        )
        delivery: StaffMessageDelivery
        text: MessageText
        template: StaffReplyTemplateView | None = None
        if reply.is_available and reply.delivery is not None:
            delivery = reply.delivery
            text = MessageText(str(input_data.text).strip())
        elif input_data.as_template and reply.template is not None:
            delivery = StaffMessageDelivery.SENT_AS_TEMPLATE
            template = reply.template
            text = template_reply_text(str(input_data.text), template)
        else:
            raise ConflictError(
                describe_block(
                    reply.block or StaffReplyBlock.UNSUPPORTED_CHANNEL,
                    conversation.channel,
                    offers_template=reply.template is not None,
                )
            )

        message: MessageDocument = MessageDocument(
            conversation_id=conversation.id,
            business_id=business.id,
            direction=MessageDirection.OUTBOUND,
            author=MessageAuthor.STAFF,
            text=text,
            language=conversation.language,
            sent_by=input_data.user_id,
            created_at=now,
            updated_at=now,
        )
        self._store(conversation, message, delivery, template, now)
        self._touch_conversation(business, conversation, now)
        self._live_events.publish(
            business.id,
            LiveEventKind.CONVERSATION_MESSAGE,
            (conversation.id,),
            is_sandbox=conversation.is_sandbox,
        )
        announce_widget_reply(self._live_events, conversation, message.id)
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.CREATE,
                entity=MESSAGE_ENTITY,
                entity_id=AuditEntityReference(str(message.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        [view] = with_staff_deliveries(
            business.id,
            [message],
            [self._message_transformer.transform(message)],
            self._outbound_message_repo,
        )
        return StaffMessageResult(message=view, delivery=delivery)

    def _store(
        self,
        conversation: ConversationDocument,
        message: MessageDocument,
        delivery: StaffMessageDelivery,
        template: StaffReplyTemplateView | None,
        now: Microseconds,
    ) -> None:
        """
        The transcript message and, for a messenger, its outbox message
        with the job that sends it: all or nothing.
        """

        outbound: OutboundMessageDocument | None = (
            None
            if delivery is StaffMessageDelivery.STORED_FOR_WIDGET
            else self._outbox.build(conversation, message, template, now)
        )
        with in_unit_of_work(self._unit_of_work):
            self._message_repo.save(message)
            if outbound is not None:
                queue_outbound_message(
                    self._outbound_message_repo,
                    self._job_queue,
                    outbound,
                    self._unit_of_work,
                )

    def _require_conversation(
        self,
        business: BusinessDocument,
        command: SendStaffMessageCommand,
    ) -> ConversationDocument:
        conversation: ConversationDocument | None = self._conversation_repo.get(
            business.id, command.conversation_id
        )
        if conversation is None:
            raise NotFoundError(
                f"Conversation {command.conversation_id} was not found."
            )

        return conversation

    def _touch_conversation(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        now: Microseconds,
    ) -> None:
        """
        Move the conversation up the feed, changing only `last_message_at` on
        the conversation as stored now, so a status the assistant set in the
        meantime (a handoff) is kept.
        """

        current: ConversationDocument = (
            self._conversation_repo.get(business.id, conversation.id) or conversation
        )
        if int(current.last_message_at) >= int(now):
            return

        current.last_message_at = now
        current.updated_at = now
        self._conversation_repo.save(current)
