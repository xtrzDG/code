"""
The customer use cases over the contacts testbed: Giorgi and Nino of
business "Sakhli" (each with a chat and a phone conversation, a booking,
a lead and calls), its owner and staff, and a stranger's business.
"""

from app.contracts.session_assurance import StepUpGuardContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.dto.contacts import ContactQuery, ContactSummaryView
from app.schemas.dto.customers.customer_card import (
    ChangeCustomerBlockingCommand,
    ChangeCustomerCardCommand,
    CustomerBlockingRequest,
    CustomerCardRequest,
    CustomerCardView,
)
from app.schemas.dto.customers.customer_segments import SegmentRulesBody
from app.schemas.dto.customers.customer_settings import (
    CustomerSettingsRequest,
    UpdateCustomerSettingsCommand,
)
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.booleans import (
    IsContactBlocked,
    IsVipCustomer,
    StaffSeesCustomerPhones,
)
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.contacts.change_customer_blocking_use_case import (
    ChangeCustomerBlockingUseCase,
)
from app.use_cases.contacts.change_customer_card_use_case import (
    ChangeCustomerCardUseCase,
)
from app.use_cases.contacts.get_contact_standing_use_case import (
    GetContactStandingUseCase,
)
from app.use_cases.contacts.get_customer_settings_use_case import (
    GetCustomerSettingsUseCase,
)
from app.use_cases.contacts.update_customer_settings_use_case import (
    UpdateCustomerSettingsUseCase,
)
from app.use_cases.shared.customer_segment_members import SegmentReaders
from tests.compliance.customer_records import Customers, seed_customers

CLIENT_IP: ClientIpAddress = ClientIpAddress("192.0.2.10")
SECONDS_PER_DAY: int = 24 * 60 * 60


class RefuseStepUp(StepUpGuardContract):
    """A session whose sign-in is too old for a sensitive action."""

    def require_recent_authentication(self) -> None:
        raise StepUpRequiredError("Confirm it is you.")


class CustomerBed:
    """The card, blocking, standing and settings use cases of `customers`."""

    def __init__(self, customers: Customers | None = None) -> None:
        self.customers: Customers = customers or seed_customers()
        testbed = self.customers.testbed
        wall_clock = testbed.clock.build_wall_clock()
        authorize = testbed.authorize_business_access
        self.readers = SegmentReaders(
            card_repo=testbed.contact_repo,
            activity_repo=testbed.contact_activity_repo,
            history_repo=testbed.customer_history_repo,
        )
        self.change_card = ChangeCustomerCardUseCase(
            authorize_business_access=authorize,
            card_repo=testbed.contact_repo,
            customer_settings_repo=testbed.customer_settings_repo,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.change_blocking = ChangeCustomerBlockingUseCase(
            authorize_business_access=authorize,
            card_repo=testbed.contact_repo,
            customer_settings_repo=testbed.customer_settings_repo,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=wall_clock,
        )
        self.get_standing = GetContactStandingUseCase(
            authorize_business_access=authorize,
            contact_repo=testbed.contact_repo,
            contact_activity_repo=testbed.contact_activity_repo,
            customer_history_repo=testbed.customer_history_repo,
            wall_clock=wall_clock,
        )
        self.get_settings = GetCustomerSettingsUseCase(
            authorize_business_access=authorize,
            customer_settings_repo=testbed.customer_settings_repo,
        )
        self.update_settings = UpdateCustomerSettingsUseCase(
            authorize_business_access=authorize,
            customer_settings_repo=testbed.customer_settings_repo,
            audit_log_repo=testbed.audit_log_repo,
            wall_clock=wall_clock,
        )

    @property
    def owner_id(self) -> UserId:
        return self.customers.owner_id

    @property
    def staff_id(self) -> UserId:
        return self.customers.staff_id

    def tag(
        self,
        contact_id: ContactId,
        *tags: str,
        user_id: UserId | None = None,
        remove: tuple[str, ...] = (),
        is_vip: bool | None = None,
    ) -> CustomerCardView:
        return self.change_card.run(
            ChangeCustomerCardCommand(
                user_id=user_id or self.owner_id,
                business_id=self.customers.business.id,
                contact_id=contact_id,
                request=CustomerCardRequest(
                    add_tags=[CustomerTag(tag) for tag in tags],
                    remove_tags=[CustomerTag(tag) for tag in remove],
                    is_vip=None if is_vip is None else IsVipCustomer(is_vip),
                ),
                client_ip_address=CLIENT_IP,
            )
        )

    def block(
        self,
        contact_id: ContactId,
        is_blocked: bool = True,
        user_id: UserId | None = None,
    ) -> CustomerCardView:
        return self.change_blocking.run(
            ChangeCustomerBlockingCommand(
                user_id=user_id or self.owner_id,
                business_id=self.customers.business.id,
                contact_id=contact_id,
                request=CustomerBlockingRequest(
                    is_blocked=IsContactBlocked(is_blocked)
                ),
                client_ip_address=CLIENT_IP,
            )
        )

    def allow_staff_phones(self, is_allowed: bool = True) -> None:
        self.update_settings.run(
            UpdateCustomerSettingsCommand(
                user_id=self.owner_id,
                business_id=self.customers.business.id,
                request=CustomerSettingsRequest(
                    staff_sees_phone_numbers=StaffSeesCustomerPhones(is_allowed)
                ),
                client_ip_address=CLIENT_IP,
            )
        )

    def add_booking(
        self,
        contact_id: ContactId,
        days_ago: int,
        status: BookingStatus = BookingStatus.COMPLETED,
    ) -> BookingDocument:
        """A booking that started `days_ago` days ago (negative: ahead)."""

        starts_at: int = (
            self.customers.testbed.clock.now_microseconds() // 1_000_000
            - days_ago * SECONDS_PER_DAY
        )
        booking = BookingDocument(
            business_id=self.customers.business.id,
            resource_id=ResourceId(),
            contact_id=contact_id,
            starts_at=BookingStartsAtUnixSeconds(starts_at),
            ends_at=BookingEndsAtUnixSeconds(starts_at + 7200),
            party_size=PartySize(2),
            status=status,
            source_channel=ChannelKind.TELEGRAM,
        )
        self.customers.testbed.booking_repo.save(booking)
        return booking

    def contact_query(
        self, contact_id: ContactId, user_id: UserId | None = None
    ) -> ContactQuery:
        return ContactQuery(
            user_id=user_id or self.owner_id,
            business_id=self.customers.business.id,
            contact_id=contact_id,
            client_ip_address=CLIENT_IP,
        )


def names_of(rows: list[ContactSummaryView]) -> list[str]:
    return [str(row.name) for row in rows]


def rules(**fields: object) -> SegmentRulesBody:
    return SegmentRulesBody.model_validate(fields)
