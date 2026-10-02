"""In-memory world for operations tests: repositories, fakes and use cases."""

from datetime import datetime

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.operations import BookingCalendarSyncFacilitatorContract
from app.facilitators.staff.manager_broadcast_facilitator import (
    ManagerBroadcastFacilitator,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.locks.business_lock_registry import BusinessLockRegistry
from app.repositories.billing_repositories import (
    SubscriptionRepository,
    UsageEventRepository,
)
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
    UnansweredQuestionRepository,
)
from app.repositories.business_repositories import (
    BusinessProfileRepository,
    BusinessRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.knowledge_repositories import (
    KnowledgeItemRepository,
    ResourceRepository,
    ScheduleExceptionRepository,
)
from app.repositories.user_repositories import UserRepository
from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.billing import SubscriptionDocument, UsageEventDocument
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessProfileDocument,
    OpeningInterval,
    ProfileAnswer,
)
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    MinNoticeMinutes,
    PartySize,
    ResourceCapacity,
    ResourceUnitCount,
    SlotDurationMinutes,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import ResourceName
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    E164PhoneNumber,
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.profiles.constrained_strings import QuestionKey
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ProfileAnswerText,
)
from app.schemas.typings.users.prefixed_id import UserId
from app.transformers.notifications.booking_cancelled_notification_transformer import (
    BookingCancelledNotificationTransformer,
)
from app.transformers.notifications.booking_confirmation_transformer import (
    BookingConfirmationTransformer,
)
from app.transformers.notifications.booking_moved_notification_transformer import (
    BookingMovedNotificationTransformer,
)
from app.transformers.notifications.cancellation_confirmation_transformer import (
    CancellationConfirmationTransformer,
)
from app.transformers.notifications.handoff_customer_message_transformer import (
    HandoffCustomerMessageTransformer,
)
from app.transformers.notifications.handoff_notification_transformer import (
    HandoffNotificationTransformer,
)
from app.transformers.notifications.new_booking_notification_transformer import (
    NewBookingNotificationTransformer,
)
from app.transformers.notifications.new_lead_notification_transformer import (
    NewLeadNotificationTransformer,
)
from app.transformers.notifications.reschedule_confirmation_transformer import (
    RescheduleConfirmationTransformer,
)
from app.use_cases.bookings.cancel_booking_use_case import CancelBookingUseCase
from app.use_cases.bookings.check_availability_use_case import CheckAvailabilityUseCase
from app.use_cases.bookings.create_booking_use_case import CreateBookingUseCase
from app.use_cases.bookings.create_manual_booking_use_case import (
    CreateManualBookingUseCase,
)
from app.use_cases.bookings.list_bookings_use_case import ListBookingsUseCase
from app.use_cases.bookings.reschedule_booking_use_case import RescheduleBookingUseCase
from app.use_cases.bookings.update_booking_use_case import UpdateBookingUseCase
from app.use_cases.handoffs.answer_unanswered_question_use_case import (
    AnswerUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.handoff_to_human_use_case import HandoffToHumanUseCase
from app.use_cases.handoffs.list_handoffs_use_case import ListHandoffsUseCase
from app.use_cases.handoffs.list_unanswered_questions_use_case import (
    ListUnansweredQuestionsUseCase,
)
from app.use_cases.handoffs.record_unanswered_question_use_case import (
    RecordUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.resolve_handoff_use_case import ResolveHandoffUseCase
from app.use_cases.insights.get_dashboard_stats_use_case import GetDashboardStatsUseCase
from app.use_cases.leads.create_lead_use_case import CreateLeadUseCase
from app.use_cases.leads.list_leads_use_case import ListLeadsUseCase
from app.use_cases.leads.update_lead_status_use_case import UpdateLeadStatusUseCase
from tests.operations.fakes import (
    FakeLocalizedTextResolver,
    MovableClock,
    PhonenumbersParser,
    RecordingCalendarSync,
    RecordingManagerNotifier,
    to_microseconds,
)

# Monday 2026-10-05 08:00 UTC = 12:00 in Tbilisi.
DEFAULT_NOW: datetime = datetime.fromisoformat("2026-10-05T08:00:00+00:00")
ALL_WEEKDAYS: tuple[Weekday, ...] = tuple(Weekday)


def minute(text: str) -> int:
    hours, minutes = text.split(":")
    return int(hours) * 60 + int(minutes)


def interval(weekday: Weekday, opens: str, closes: str) -> OpeningInterval:
    closes_minute: int = minute(closes) or 24 * 60
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(minute(opens)),
        closes_at=ClosingMinuteOfDay(closes_minute),
    )


def every_day(opens: str, closes: str) -> list[OpeningInterval]:
    return [interval(weekday, opens, closes) for weekday in ALL_WEEKDAYS]


def manager(
    name: str,
    channel: ManagerContactChannel,
    address: str,
    language: str,
) -> ManagerContact:
    return ManagerContact(
        name=ManagerName(name),
        channel=channel,
        address=ManagerContactAddress(address),
        language=LanguageTag(language),
    )


DEFAULT_MANAGERS: tuple[ManagerContact, ...] = (
    manager("Nino", ManagerContactChannel.TELEGRAM, "4242", "ka"),
    manager("Daniel", ManagerContactChannel.WHATSAPP, "+995555000111", "ru"),
    manager("Anna", ManagerContactChannel.EMAIL, "anna@example.com", "en"),
)


class OperationsWorld:
    """Everything the operations use cases need, wired in memory."""

    def __init__(self, now: datetime = DEFAULT_NOW) -> None:
        self.clock = MovableClock(now)
        self.business_repo = BusinessRepository(
            InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
        )
        self.profile_repo = BusinessProfileRepository(
            InMemoryDocumentCollectionAdapter[BusinessProfileDocument](
                BusinessProfileDocument
            )
        )
        self.resource_repo = ResourceRepository(
            InMemoryDocumentCollectionAdapter[ResourceDocument](ResourceDocument)
        )
        self.exception_repo = ScheduleExceptionRepository(
            InMemoryDocumentCollectionAdapter[ScheduleExceptionDocument](
                ScheduleExceptionDocument
            )
        )
        self.booking_repo = BookingRepository(
            InMemoryDocumentCollectionAdapter[BookingDocument](BookingDocument)
        )
        self.contact_repo = ContactRepository(
            InMemoryDocumentCollectionAdapter[ContactDocument](ContactDocument)
        )
        self.conversation_repo = ConversationRepository(
            InMemoryDocumentCollectionAdapter[ConversationDocument](
                ConversationDocument
            )
        )
        self.message_repo = MessageRepository(
            InMemoryDocumentCollectionAdapter[MessageDocument](MessageDocument)
        )
        self.lead_repo = LeadRepository(
            InMemoryDocumentCollectionAdapter[LeadDocument](LeadDocument)
        )
        self.handoff_repo = HandoffRepository(
            InMemoryDocumentCollectionAdapter[HandoffDocument](HandoffDocument)
        )
        self.question_repo = UnansweredQuestionRepository(
            InMemoryDocumentCollectionAdapter[UnansweredQuestionDocument](
                UnansweredQuestionDocument
            )
        )
        self.knowledge_repo = KnowledgeItemRepository(
            InMemoryDocumentCollectionAdapter[KnowledgeItemDocument](
                KnowledgeItemDocument
            )
        )
        self.usage_repo = UsageEventRepository(
            InMemoryDocumentCollectionAdapter[UsageEventDocument](UsageEventDocument)
        )
        self.subscription_repo = SubscriptionRepository(
            InMemoryDocumentCollectionAdapter[SubscriptionDocument](
                SubscriptionDocument
            )
        )
        self.plan_registry = PlanRegistry()
        self.audit_repo = AuditLogRepository(
            InMemoryDocumentCollectionAdapter[AuditLogEntryDocument](
                AuditLogEntryDocument
            )
        )
        self.user_repo = UserRepository(
            InMemoryDocumentCollectionAdapter[UserDocument](UserDocument)
        )
        self.resolver = FakeLocalizedTextResolver()
        self.phone_parser = PhonenumbersParser()
        self.notifier = RecordingManagerNotifier()
        self.broadcaster = ManagerBroadcastFacilitator(self.notifier)
        self.calendar_sync = RecordingCalendarSync()
        self.lock_registry = BusinessLockRegistry()

    # Data

    def add_business(
        self,
        name: str = "Salobie Bia",
        country_code: str = "GE",
        timezone: str = "Asia/Tbilisi",
        currency_code: str = "GEL",
        languages: tuple[str, ...] = ("ka", "ru", "en"),
        owner_language: str = "ru",
        niche_key: NicheKey = NicheKey.RESTAURANT,
        managers: tuple[ManagerContact, ...] = DEFAULT_MANAGERS,
        owner_id: UserId | None = None,
        staff_ids: tuple[UserId, ...] = (),
    ) -> BusinessDocument:
        members: list[BusinessMember] = [
            BusinessMember(user_id=owner_id or UserId(), role=BusinessMemberRole.OWNER),
            *[
                BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF)
                for staff_id in staff_ids
            ],
        ]
        business = BusinessDocument(
            name=BusinessName(name),
            niche_key=niche_key,
            country_code=CountryCode(country_code),
            timezone=TimezoneName(timezone),
            currency_code=CurrencyCode(currency_code),
            languages=[LanguageTag(language) for language in languages],
            default_language=LanguageTag(languages[0]),
            owner_language=LanguageTag(owner_language),
            plan_key=PlanKey.VOICE_AND_CHAT,
            data_region=DataRegion.EU,
            members=members,
            manager_contacts=list(managers),
        )
        self.business_repo.save(business)
        return business

    def add_profile(
        self,
        business: BusinessDocument,
        hours: list[OpeningInterval] | None = None,
        resource_kind: ResourceKind = ResourceKind.TABLE,
        slot_minutes: int = 120,
        max_party_size: int = 12,
        min_notice_minutes: int = 60,
        cancellation_policy: str | None = "Free cancellation up to 2 hours before.",
        niche_answers: dict[str, str] | None = None,
        has_booking_rules: bool = True,
    ) -> BusinessProfileDocument:
        profile = BusinessProfileDocument(
            business_id=business.id,
            niche_key=business.niche_key,
            answers_language=business.owner_language,
            hours=every_day("12:00", "23:00") if hours is None else hours,
            booking_rules=(
                BookingRules(
                    resource_kind=resource_kind,
                    slot_minutes=SlotDurationMinutes(slot_minutes),
                    max_party_size=PartySize(max_party_size),
                    min_notice_minutes=MinNoticeMinutes(min_notice_minutes),
                    cancellation_policy=(
                        None
                        if cancellation_policy is None
                        else CancellationPolicyText(cancellation_policy)
                    ),
                )
                if has_booking_rules
                else None
            ),
            niche_answers=[
                ProfileAnswer(
                    question_key=QuestionKey(key), answer=ProfileAnswerText(value)
                )
                for key, value in (niche_answers or {}).items()
            ],
        )
        self.profile_repo.save(profile)
        return profile

    def add_resource(
        self,
        business: BusinessDocument,
        name: str,
        capacity: int = 4,
        unit_count: int = 1,
        kind: ResourceKind = ResourceKind.TABLE,
        booking_unit: BookingUnit = BookingUnit.TIME_SLOT,
        slot_minutes: int | None = None,
        schedule: list[OpeningInterval] | None = None,
        is_active: bool = True,
    ) -> ResourceDocument:
        resource = ResourceDocument(
            business_id=business.id,
            kind=kind,
            name=ResourceName(name),
            capacity=ResourceCapacity(capacity),
            unit_count=ResourceUnitCount(unit_count),
            booking_unit=booking_unit,
            slot_minutes=(
                None if slot_minutes is None else SlotDurationMinutes(slot_minutes)
            ),
            schedule=schedule or [],
            is_active=is_active,
        )
        self.resource_repo.save(resource)
        return resource

    def add_exception(
        self,
        business: BusinessDocument,
        date: str,
        resource: ResourceDocument | None = None,
        special_hours: list[OpeningInterval] | None = None,
        is_closed_all_day: bool | None = None,
    ) -> ScheduleExceptionDocument:
        exception = ScheduleExceptionDocument(
            business_id=business.id,
            resource_id=None if resource is None else resource.id,
            date=LocalDate(date),
            is_closed_all_day=(
                not special_hours if is_closed_all_day is None else is_closed_all_day
            ),
            special_hours=special_hours or [],
        )
        self.exception_repo.save(exception)
        return exception

    def add_contact(
        self,
        business: BusinessDocument,
        name: str | None = None,
        phone: str | None = None,
        language: str | None = None,
    ) -> ContactDocument:
        contact = ContactDocument(
            business_id=business.id,
            name=None if name is None else ContactName(name),
            phone_number=None if phone is None else E164PhoneNumber(phone),
            language=None if language is None else LanguageTag(language),
        )
        self.contact_repo.save(contact)
        return contact

    def add_conversation(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        channel: ChannelKind = ChannelKind.WHATSAPP,
        language: str | None = "ka",
        is_sandbox: bool = False,
        is_after_hours: bool = False,
        created_at: datetime | None = None,
    ) -> ConversationDocument:
        moment = (
            self.clock.now_microseconds()
            if created_at is None
            else to_microseconds(created_at)
        )
        conversation = ConversationDocument(
            business_id=business.id,
            contact_id=contact.id,
            assistant_version_id=AssistantVersionId(),
            channel=channel,
            channel_user_id=ChannelUserId("customer-1"),
            language=None if language is None else LanguageTag(language),
            is_sandbox=is_sandbox,
            is_after_hours=is_after_hours,
            last_message_at=moment,
            created_at=moment,
            updated_at=moment,
        )
        self.conversation_repo.save(conversation)
        return conversation

    def add_booking(
        self,
        business: BusinessDocument,
        resource: ResourceDocument,
        contact: ContactDocument,
        starts: str,
        ends: str,
        status: BookingStatus = BookingStatus.CONFIRMED,
        is_sandbox: bool = False,
        party_size: int = 2,
    ) -> BookingDocument:
        """Booking between two ISO datetimes with offsets."""

        booking = BookingDocument(
            business_id=business.id,
            resource_id=resource.id,
            contact_id=contact.id,
            starts_at=BookingStartsAtUnixSeconds(
                int(datetime.fromisoformat(starts).timestamp())
            ),
            ends_at=BookingEndsAtUnixSeconds(
                int(datetime.fromisoformat(ends).timestamp())
            ),
            party_size=PartySize(party_size),
            status=status,
            source_channel=ChannelKind.PHONE,
            is_sandbox=is_sandbox,
        )
        self.booking_repo.save(booking)
        return booking

    def bookings_of(self, business_id: BusinessId) -> list[BookingDocument]:
        return self.booking_repo.list_by_business(business_id)

    # Use cases

    def check_availability(self) -> CheckAvailabilityUseCase:
        return CheckAvailabilityUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            wall_clock=self.clock.wall_clock,
        )

    def create_booking(
        self,
        calendar_sync: BookingCalendarSyncFacilitatorContract | None = None,
    ) -> CreateBookingUseCase:
        return CreateBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=BookingConfirmationTransformer(self.resolver),
            staff_notification_transformer=NewBookingNotificationTransformer(
                self.resolver
            ),
            manager_broadcaster=self.broadcaster,
            calendar_sync=calendar_sync or self.calendar_sync,
            wall_clock=self.clock.wall_clock,
        )

    def cancel_booking(self) -> CancelBookingUseCase:
        return CancelBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=CancellationConfirmationTransformer(self.resolver),
            staff_notification_transformer=BookingCancelledNotificationTransformer(
                self.resolver
            ),
            manager_broadcaster=self.broadcaster,
            calendar_sync=self.calendar_sync,
            wall_clock=self.clock.wall_clock,
        )

    def reschedule_booking(self) -> RescheduleBookingUseCase:
        return RescheduleBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=RescheduleConfirmationTransformer(self.resolver),
            staff_notification_transformer=BookingMovedNotificationTransformer(
                self.resolver
            ),
            manager_broadcaster=self.broadcaster,
            calendar_sync=self.calendar_sync,
            wall_clock=self.clock.wall_clock,
        )

    def list_bookings(self) -> ListBookingsUseCase:
        return ListBookingsUseCase(
            business_repo=self.business_repo,
            booking_repo=self.booking_repo,
            resource_repo=self.resource_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
        )

    def create_manual_booking(self) -> CreateManualBookingUseCase:
        return CreateManualBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            audit_log_repo=self.audit_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=BookingConfirmationTransformer(self.resolver),
            calendar_sync=self.calendar_sync,
            wall_clock=self.clock.wall_clock,
        )

    def update_booking(self) -> UpdateBookingUseCase:
        return UpdateBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            resource_repo=self.resource_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            lock_registry=self.lock_registry,
            calendar_sync=self.calendar_sync,
            wall_clock=self.clock.wall_clock,
        )

    def create_lead(self) -> CreateLeadUseCase:
        return CreateLeadUseCase(
            business_repo=self.business_repo,
            lead_repo=self.lead_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            phone_number_parser=self.phone_parser,
            staff_notification_transformer=NewLeadNotificationTransformer(
                self.resolver
            ),
            manager_broadcaster=self.broadcaster,
            wall_clock=self.clock.wall_clock,
        )

    def list_leads(self) -> ListLeadsUseCase:
        return ListLeadsUseCase(
            business_repo=self.business_repo,
            lead_repo=self.lead_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
        )

    def update_lead_status(self) -> UpdateLeadStatusUseCase:
        return UpdateLeadStatusUseCase(
            lead_repo=self.lead_repo,
            wall_clock=self.clock.wall_clock,
        )

    def handoff_to_human(self) -> HandoffToHumanUseCase:
        return HandoffToHumanUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            conversation_repo=self.conversation_repo,
            contact_repo=self.contact_repo,
            handoff_repo=self.handoff_repo,
            phone_number_parser=self.phone_parser,
            staff_notification_transformer=HandoffNotificationTransformer(
                self.resolver
            ),
            customer_message_transformer=HandoffCustomerMessageTransformer(
                self.resolver
            ),
            manager_broadcaster=self.broadcaster,
            wall_clock=self.clock.wall_clock,
        )

    def resolve_handoff(self) -> ResolveHandoffUseCase:
        return ResolveHandoffUseCase(
            handoff_repo=self.handoff_repo,
            conversation_repo=self.conversation_repo,
            contact_repo=self.contact_repo,
            wall_clock=self.clock.wall_clock,
        )

    def list_handoffs(self) -> ListHandoffsUseCase:
        return ListHandoffsUseCase(
            business_repo=self.business_repo,
            handoff_repo=self.handoff_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
        )

    def record_unanswered_question(self) -> RecordUnansweredQuestionUseCase:
        return RecordUnansweredQuestionUseCase(
            business_repo=self.business_repo,
            unanswered_question_repo=self.question_repo,
            wall_clock=self.clock.wall_clock,
        )

    def list_unanswered_questions(self) -> ListUnansweredQuestionsUseCase:
        return ListUnansweredQuestionsUseCase(
            unanswered_question_repo=self.question_repo
        )

    def answer_unanswered_question(self) -> AnswerUnansweredQuestionUseCase:
        return AnswerUnansweredQuestionUseCase(
            unanswered_question_repo=self.question_repo,
            knowledge_item_repo=self.knowledge_repo,
            wall_clock=self.clock.wall_clock,
        )

    def dashboard(self) -> GetDashboardStatsUseCase:
        return GetDashboardStatsUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            unanswered_question_repo=self.question_repo,
            usage_event_repo=self.usage_repo,
            subscription_repo=self.subscription_repo,
            plan_registry=self.plan_registry,
            wall_clock=self.clock.wall_clock,
        )
