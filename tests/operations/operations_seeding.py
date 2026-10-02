"""Seeding the operations world: businesses, profiles, resources, bookings."""

from datetime import datetime

from app.schemas.constants.billing import PlanKey
from app.schemas.constants.bookings import BookingStatus, BookingUnit, ResourceKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.localization import DataRegion
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import (
    BusinessDocument,
    BusinessMember,
    ManagerContact,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessProfileDocument,
    OpeningInterval,
    ProfileAnswer,
)
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
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
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import ChannelUserId
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
from tests.operations.builders import DEFAULT_MANAGERS, every_day
from tests.operations.fakes import (
    to_microseconds,
)
from tests.operations.operations_store import OperationsStore


class OperationsSeeding(OperationsStore):
    """The operations store with helpers that add test data to it."""

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
