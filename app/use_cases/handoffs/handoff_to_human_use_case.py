from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.booking_repositories import HandoffRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.handoffs import HandoffStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.handoffs import (
    CodedHandoffSummary,
    HandoffCommand,
    HandoffResult,
    HandoffSummaryInput,
)
from app.schemas.dto.notifications.staff_alerts import (
    HandoffBrief,
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.dto.operations.message_texts import (
    HandoffCustomerMessageInput,
    HandoffStaffNotificationInput,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.use_cases.bookings.operations_support import (
    display_phone,
    require_business,
)
from app.use_cases.handoffs.handoff_reopening import build_customer_message_input
from app.use_cases.notifications.staff_alerts import StaffAlertTexts, handoff_alert


class HandoffToHumanUseCase(UseCaseContract[HandoffCommand, HandoffResult]):
    """
    Pass a conversation to staff (model tool handoff_to_human).

    The handoff is stored with its urgency and the conversation switches to
    HANDOFF, so the assistant stays silent in chat until staff resolve it.
    Every staff contact is notified in their language (linked chats with the
    reason, urgency, summary, the customer's name, phone in international
    format and channel; e-mail, SMS and devices briefly), each with a link
    to the conversation. The notifications go through the outbox: the
    handoff stays
    PENDING until one is delivered (NOTIFIED) or they fail
    (NOTIFICATION_FAILED); it is NOTIFICATION_FAILED at once when no contact
    can be reached. Sandbox handoffs notify nobody and stay PENDING.

    The customer is told, in their language, that a colleague replies soon
    (during opening hours, or when hours are unknown) or when the business
    opens, with the local opening date and time.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        conversation_repo: ConversationRepoContract,
        contact_repo: ContactRepoContract,
        handoff_repo: HandoffRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        staff_notification_transformer: TransformerContract[
            HandoffStaffNotificationInput, MessageText
        ],
        customer_message_transformer: TransformerContract[
            HandoffCustomerMessageInput, MessageText
        ],
        live_events: EventPublisherFacilitatorContract,
        staff_brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ],
        staff_alerts: StaffAlertFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        summary_transformer: TransformerContract[HandoffSummaryInput, HandoffSummary],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._staff_notification_transformer: TransformerContract[
            HandoffStaffNotificationInput, MessageText
        ] = staff_notification_transformer
        self._customer_message_transformer: TransformerContract[
            HandoffCustomerMessageInput, MessageText
        ] = customer_message_transformer
        self._staff_brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ] = staff_brief_transformer
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._summary_transformer: TransformerContract[
            HandoffSummaryInput, HandoffSummary
        ] = summary_transformer

    def run(self, input_data: HandoffCommand) -> HandoffResult:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        conversation: ConversationDocument | None = self._conversation_repo.get(
            business.id, input_data.conversation_id
        )
        if conversation is None:
            raise NotFoundError(
                f"Conversation {input_data.conversation_id} was not found."
            )

        now: Microseconds = self._wall_clock.now_unix()
        coded: CodedHandoffSummary | None = (
            input_data.summary
            if isinstance(input_data.summary, CodedHandoffSummary)
            else None
        )
        handoff = HandoffDocument(
            business_id=business.id,
            conversation_id=conversation.id,
            contact_id=input_data.contact_id,
            reason=input_data.reason,
            summary=self._summary(input_data, business.owner_language),
            summary_code=None if coded is None else coded.code,
            quoted_text=None if coded is None else coded.quoted_text,
            flagged_values=[] if coded is None else list(coded.flagged_values),
            urgency=input_data.urgency,
            status=HandoffStatus.PENDING,
            is_sandbox=input_data.is_sandbox,
            created_at=now,
            updated_at=now,
        )
        self._handoff_repo.save(handoff)
        conversation.status = ConversationStatus.HANDOFF
        conversation.updated_at = now
        self._conversation_repo.save(conversation)

        if not input_data.is_sandbox:
            queued: DeliveredNotificationCount = self._notify_staff(
                business, input_data, handoff
            )
            if int(queued) == 0:
                # Nobody can be reached. When notifications are queued, the
                # outbox moves the handoff on as they are delivered.
                handoff.status = HandoffStatus.NOTIFICATION_FAILED
                handoff.updated_at = now
                self._handoff_repo.save(handoff)

        self._live_events.publish(
            business.id,
            LiveEventKind.HANDOFF_CREATED,
            (handoff.id, conversation.id),
            is_sandbox=handoff.is_sandbox,
        )
        return HandoffResult(
            id=handoff.id,
            business_id=business.id,
            conversation_id=conversation.id,
            reason=handoff.reason,
            urgency=handoff.urgency,
            status=handoff.status,
            customer_message=self._customer_message_transformer.transform(
                build_customer_message_input(
                    business,
                    input_data.language,
                    now,
                    self._business_profile_repo.get_by_business(business.id),
                    self._schedule_exception_repo,
                )
            ),
        )

    def _notify_staff(
        self,
        business: BusinessDocument,
        command: HandoffCommand,
        handoff: HandoffDocument,
    ) -> DeliveredNotificationCount:
        contact: ContactDocument | None = self._contact_repo.get(
            business.id, command.contact_id
        )
        phone: FormattedPhoneNumber | None = display_phone(
            self._phone_number_parser,
            None if contact is None else contact.phone_number,
        )

        def render(language: LanguageTag) -> MessageText:
            return self._staff_notification_transformer.transform(
                HandoffStaffNotificationInput(
                    business_name=business.name,
                    reason=command.reason,
                    urgency=command.urgency,
                    summary=self._summary(command, language),
                    contact_name=None if contact is None else contact.name,
                    contact_phone_display=phone,
                    channel=command.source_channel,
                    language=language,
                )
            )

        def render_brief(language: LanguageTag) -> StaffAlertBrief:
            return self._staff_brief_transformer.transform(
                StaffAlertBriefInput(
                    business_name=business.name,
                    language=language,
                    handoff=HandoffBrief(
                        reason=command.reason, urgency=command.urgency
                    ),
                )
            )

        return self._staff_alerts.alert(
            business,
            handoff_alert(
                business.id, handoff.id, handoff.conversation_id, command.urgency
            ),
            StaffAlertTexts(detailed=render, brief=render_brief),
        )

    def _summary(
        self, command: HandoffCommand, language: LanguageTag
    ) -> HandoffSummary:
        """The model's own summary, or the platform's rendered in `language`."""

        if isinstance(command.summary, CodedHandoffSummary):
            return self._summary_transformer.transform(
                HandoffSummaryInput(summary=command.summary, language=language)
            )

        return command.summary
