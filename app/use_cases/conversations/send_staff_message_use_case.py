from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.conversations import (
    MessageAuthor,
    StaffMessageDelivery,
    StaffReplyBlock,
    StaffReplyRefusalCode,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_actions import (
    SendStaffMessageCommand,
    StaffMessageResult,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    MessageView,
    StaffReplyView,
)
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.staff_reply_templates import StaffReplyTemplateView
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
    WhatsAppTemplateRejectedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.conversations.constrained_strings import (
    StaffTemplateReplyText,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.use_cases.conversations.staff_reply_support import (
    assess_conversation_reply,
)
from app.utilities.conversations.staff_replies import (
    describe_block,
    to_template_parameter,
)

MESSAGE_ENTITY: AuditEntityName = AuditEntityName("message")
TEMPLATE_REJECTED_MESSAGE: str = (
    "WhatsApp did not accept the message template for staff replies: check "
    "its name, its language and its one {{1}} variable in the channel "
    "settings."
)


class SendStaffMessageUseCase(
    UseCaseContract[SendStaffMessageCommand, StaffMessageResult]
):
    """
    An owner or staff member writes to the customer of a conversation from
    the cabinet (concept section 6: after a handoff a person answers in the
    same channel).

    Telegram, WhatsApp, Instagram and Messenger messages are sent through
    the business's connected channel right away; WhatsApp, Instagram and
    Messenger only within 24 hours of the customer's last message there.
    After that, a WhatsApp message asked to go `as_template` travels in the
    message template the owner set for staff replies, in its approved
    language, as its single body parameter: one line (line breaks become
    spaces) of at most 1024 characters, else ValidationFailedError. A
    template Meta refuses (no approved template of that name in that
    language, other variables) is a ConflictError with the reason
    `template_rejected`: trying again cannot help. Website chat messages
    are kept for the visitor's widget. Phone and test conversations cannot
    be written to; every refusal is a ConflictError that says why. The
    message is stored in the transcript as a STAFF message with its author,
    the conversation moves up the feed, the assistant is not asked to
    answer, and the message (personal data) is written to the audit log.
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
        channel_message_sender: ChannelMessageSenderFacilitatorContract,
        message_transformer: TransformerContract[MessageDocument, MessageView],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._channel_repo: ChannelRepoContract = channel_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._channel_message_sender: ChannelMessageSenderFacilitatorContract = (
            channel_message_sender
        )
        self._message_transformer: TransformerContract[MessageDocument, MessageView] = (
            message_transformer
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

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
            now,
        )
        delivery: StaffMessageDelivery
        text: MessageText
        if reply.is_available and reply.delivery is not None:
            delivery = reply.delivery
            text = MessageText(str(input_data.text).strip())
            if delivery is StaffMessageDelivery.SENT:
                self._channel_message_sender.send(
                    business.id,
                    conversation.channel,
                    conversation.channel_user_id,
                    text,
                )
        elif input_data.as_template and reply.template is not None:
            delivery = StaffMessageDelivery.SENT_AS_TEMPLATE
            text = self._send_as_template(
                business, conversation, reply.template, input_data
            )
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
        self._message_repo.save(message)
        self._touch_conversation(business, conversation, now)
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
        return StaffMessageResult(
            message=self._message_transformer.transform(message),
            delivery=delivery,
        )

    def _send_as_template(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        template: StaffReplyTemplateView,
        command: SendStaffMessageCommand,
    ) -> MessageText:
        """Send the staff text in the owner's template; returns what was sent."""

        try:
            parameter: StaffTemplateReplyText = to_template_parameter(str(command.text))
        except ValueError as error:
            raise ValidationFailedError(
                "A message sent as a WhatsApp template may have at most "
                f"{template.max_text_length} characters (line breaks are sent "
                "as spaces)."
            ) from error

        text: MessageText = MessageText(str(parameter))
        try:
            self._channel_message_sender.send_whatsapp_template_in_language(
                business.id,
                conversation.channel_user_id,
                template.name,
                template.language_code,
                [text],
            )
        except WhatsAppTemplateRejectedError as error:
            # Trying again cannot help: the template setting is wrong.
            raise ConflictError(
                TEMPLATE_REJECTED_MESSAGE,
                reasons=[
                    ErrorReason(
                        code=ErrorReasonCode(
                            StaffReplyRefusalCode.TEMPLATE_REJECTED.value
                        ),
                        message=ErrorReasonMessage(str(error)),
                        details=[
                            ErrorReasonDetail(str(template.name)),
                            ErrorReasonDetail(str(template.language_code)),
                        ],
                    )
                ],
            ) from error

        return text

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
