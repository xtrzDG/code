"""Steps shared by the booking use cases: loading scheduling inputs and
finding the booking a customer refers to."""

from datetime import date
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.notifications import StaffBookingChange
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import (
    BookingRules,
    BusinessProfileDocument,
    OpeningInterval,
)
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.notifications.staff_alerts import (
    BookingBrief,
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.dto.operations.message_texts import BookingStaffNotificationInput
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.use_cases.bookings.operations_support import (
    display_phone,
    require_business,
)
from app.use_cases.notifications.staff_alerts import StaffAlertTexts, booking_alert
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.nights import StayTimes, read_stay_times
from app.utilities.scheduling.zoned_time import load_time_zone, to_local_moment


class SchedulingInputs(NamedTuple):
    """A business with everything its availability depends on."""

    business: BusinessDocument
    zone: ZoneInfo
    profile: BusinessProfileDocument | None
    rules: BookingRules | None
    business_hours: list[OpeningInterval]
    stay_times: StayTimes
    resources: list[ResourceDocument]
    exceptions: list[ScheduleExceptionDocument]


def load_scheduling_inputs(
    business_repo: BusinessRepoContract,
    business_profile_repo: BusinessProfileRepoContract,
    resource_repo: ResourceRepoContract,
    schedule_exception_repo: ScheduleExceptionRepoContract,
    business_id: BusinessId,
) -> SchedulingInputs:
    business: BusinessDocument = require_business(business_repo, business_id)
    profile: BusinessProfileDocument | None = business_profile_repo.get_by_business(
        business_id
    )
    return SchedulingInputs(
        business=business,
        zone=load_time_zone(business.timezone),
        profile=profile,
        rules=None if profile is None else profile.booking_rules,
        business_hours=[] if profile is None else list(profile.hours),
        stay_times=read_stay_times(profile),
        resources=resource_repo.list_by_business(business_id),
        exceptions=schedule_exception_repo.list_by_business(business_id),
    )


def notify_staff_about_booking(
    staff_alerts: StaffAlertFacilitatorContract,
    notification_transformer: TransformerContract[
        BookingStaffNotificationInput, MessageText
    ],
    brief_transformer: TransformerContract[StaffAlertBriefInput, StaffAlertBrief],
    phone_number_parser: PhoneNumberParserContract,
    business: BusinessDocument,
    view: BookingView,
    change: StaffBookingChange,
) -> None:
    """
    Tell every staff contact and subscribed device about a booking, each in
    their own language, with a link to the bookings of its day.
    """

    phone: FormattedPhoneNumber | None = display_phone(
        phone_number_parser, view.contact_phone_number
    )

    def render(language: LanguageTag) -> MessageText:
        return notification_transformer.transform(
            BookingStaffNotificationInput(
                business_name=business.name,
                booking=view,
                contact_phone_display=phone,
                language=language,
            )
        )

    def render_brief(language: LanguageTag) -> StaffAlertBrief:
        return brief_transformer.transform(
            StaffAlertBriefInput(
                business_name=business.name,
                language=language,
                booking=BookingBrief(booking=view, change=change),
            )
        )

    staff_alerts.alert(
        business,
        booking_alert(view),
        StaffAlertTexts(detailed=render, brief=render_brief),
    )


def find_resource(
    resources: list[ResourceDocument],
    resource_id: ResourceId,
) -> ResourceDocument | None:
    for resource in resources:
        if resource.id == resource_id:
            return resource

    return None


def booking_unit_of(resource: ResourceDocument | None) -> BookingUnit:
    return BookingUnit.TIME_SLOT if resource is None else resource.booking_unit


def stay_night_count(booking: BookingDocument, zone: ZoneInfo) -> int:
    """Nights of a stay from its local check-in and check-out dates."""

    check_in: date = to_local_moment(int(booking.starts_at), zone).date()
    check_out: date = to_local_moment(int(booking.ends_at), zone).date()
    return max((check_out - check_in).days, 1)


def find_customer_contact_ids(
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    contact_id: ContactId | None,
    phone_number: E164PhoneNumber | None,
) -> set[ContactId]:
    """The contact itself plus every contact of the business with the phone."""

    contact_ids: set[ContactId] = set()
    if contact_id is not None:
        contact_ids.add(contact_id)

    if phone_number is not None:
        contact_ids.update(
            contact.id
            for contact in contact_repo.list_by_business(business_id)
            if contact.phone_number == phone_number
        )

    return contact_ids


def find_target_booking(
    booking_repo: BookingRepoContract,
    contact_repo: ContactRepoContract,
    business_id: BusinessId,
    zone: ZoneInfo,
    booking_id: BookingId | None,
    contact_id: ContactId | None,
    phone_number: E164PhoneNumber | None,
    local_date: date | None,
    now_seconds: int,
    is_sandbox: bool | None = None,
) -> BookingDocument:
    """
    The booking a cancel or reschedule refers to.

    By id: it must belong to the business, and to the customer when the
    command carries the customer's contact or phone (the model cannot reach
    someone else's booking). Otherwise the customer's active bookings on the
    local date (or all upcoming ones without a date) must match exactly one.
    The phone must be one the channel proved for the customer (the caller
    passes only such a phone). With `is_sandbox` set, only bookings of that
    sandbox mode count, so an owner test never reaches a real booking.

    Raises:
        NotFoundError: no such booking for this customer.
        ConflictError: several bookings match; ask for the date, time or id.
        ValidationFailedError: neither an id nor the customer is given.
    """

    customer_contact_ids: set[ContactId] = find_customer_contact_ids(
        contact_repo, business_id, contact_id, phone_number
    )
    if booking_id is not None:
        booking: BookingDocument | None = booking_repo.get(business_id, booking_id)
        is_customer_request: bool = contact_id is not None or phone_number is not None
        if (
            booking is None
            or (is_customer_request and booking.contact_id not in customer_contact_ids)
            or (is_sandbox is not None and booking.is_sandbox != is_sandbox)
        ):
            raise NotFoundError(f"Booking {booking_id} was not found.")

        return booking

    if not customer_contact_ids:
        raise ValidationFailedError(
            "Give the booking id, or the customer's contact or phone and the date."
        )

    candidates: list[BookingDocument] = [
        booking
        for booking in booking_repo.list_by_business(business_id)
        if booking.contact_id in customer_contact_ids
        and booking.status in BLOCKING_BOOKING_STATUSES
        and (is_sandbox is None or booking.is_sandbox == is_sandbox)
    ]
    if local_date is None:
        candidates = [
            booking for booking in candidates if int(booking.ends_at) > now_seconds
        ]
    else:
        candidates = [
            booking
            for booking in candidates
            if to_local_moment(int(booking.starts_at), zone).date() == local_date
        ]

    if not candidates:
        raise NotFoundError("No active booking was found for this customer.")

    if len(candidates) > 1:
        raise ConflictError(
            f"{len(candidates)} bookings match; ask the customer for the date and "
            "time, or use the booking id."
        )

    return candidates[0]
