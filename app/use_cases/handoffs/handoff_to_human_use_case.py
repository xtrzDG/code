from datetime import datetime
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.operations import ManagerBroadcastFacilitatorContract
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
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.profiles import BusinessProfileDocument, OpeningInterval
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.operations import (
    HandoffCustomerMessageInput,
    HandoffStaffNotificationInput,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.use_cases.bookings.operations_support import (
    build_staff_messages,
    display_phone,
    require_business,
)
from app.utilities.scheduling.opening_hours import (
    business_day_ranges,
    find_next_opening,
    is_open_at,
)
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    minute_of_day,
    to_local_date,
    to_time_of_day,
)


class HandoffToHumanUseCase(UseCaseContract[HandoffCommand, HandoffResult]):
    """
    Pass a conversation to staff (model tool handoff_to_human).

    The handoff is stored with its urgency and the conversation switches to
    HANDOFF, so the assistant stays silent in chat until staff resolve it.
    Every staff contact is notified in their language with the reason,
    urgency, summary, the customer's name, phone in international format and
    channel: the handoff becomes NOTIFIED when at least one notification was
    delivered, NOTIFICATION_FAILED otherwise. Sandbox handoffs notify nobody
    and stay PENDING.

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
        manager_broadcaster: ManagerBroadcastFacilitatorContract,
        wall_clock: WallClock[Microseconds],
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
        self._manager_broadcaster: ManagerBroadcastFacilitatorContract = (
            manager_broadcaster
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

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
        handoff = HandoffDocument(
            business_id=business.id,
            conversation_id=conversation.id,
            contact_id=input_data.contact_id,
            reason=input_data.reason,
            summary=input_data.summary,
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
            delivered: DeliveredNotificationCount = self._notify_staff(
                business, input_data
            )
            handoff.status = (
                HandoffStatus.NOTIFIED
                if int(delivered) > 0
                else HandoffStatus.NOTIFICATION_FAILED
            )
            handoff.updated_at = now
            self._handoff_repo.save(handoff)

        return HandoffResult(
            id=handoff.id,
            business_id=business.id,
            conversation_id=conversation.id,
            reason=handoff.reason,
            urgency=handoff.urgency,
            status=handoff.status,
            customer_message=self._customer_message_transformer.transform(
                self._customer_message_input(business, input_data.language, now)
            ),
        )

    def _notify_staff(
        self,
        business: BusinessDocument,
        command: HandoffCommand,
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
                    summary=command.summary,
                    contact_name=None if contact is None else contact.name,
                    contact_phone_display=phone,
                    channel=command.source_channel,
                    language=language,
                )
            )

        return self._manager_broadcaster.broadcast(
            build_staff_messages(business, render)
        )

    def _customer_message_input(
        self,
        business: BusinessDocument,
        language: LanguageTag,
        now: Microseconds,
    ) -> HandoffCustomerMessageInput:
        profile: BusinessProfileDocument | None = (
            self._business_profile_repo.get_by_business(business.id)
        )
        hours: list[OpeningInterval] = [] if profile is None else list(profile.hours)
        if not hours:
            return HandoffCustomerMessageInput(language=language)

        zone: ZoneInfo = load_time_zone(business.timezone)
        ranges_starting_on = business_day_ranges(
            hours, self._schedule_exception_repo.list_by_business(business.id)
        )
        now_seconds: int = microseconds_to_seconds(int(now))
        if is_open_at(now_seconds, zone, ranges_starting_on):
            return HandoffCustomerMessageInput(language=language)

        reopening: datetime | None = find_next_opening(
            now_seconds, zone, ranges_starting_on
        )
        if reopening is None:
            return HandoffCustomerMessageInput(language=language)

        return HandoffCustomerMessageInput(
            language=language,
            reopens_on=to_local_date(reopening.date()),
            reopens_at=to_time_of_day(minute_of_day(reopening)),
        )
