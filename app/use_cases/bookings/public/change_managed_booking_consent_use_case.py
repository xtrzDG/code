from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.consent_repositories import ConsentRecordRepoContract
from app.contracts.repositories.customer_repositories import CustomerCardRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.consent_records import ConsentEventSource
from app.schemas.constants.marketing_consent import (
    MarketingConsentSource,
    MarketingConsentText,
    MarketingConsentWithdrawal,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument, MarketingConsent
from app.schemas.dto.booking_manage import ManagedBookingAction, ManagedBookingView
from app.schemas.dto.customers.consent_records import ConsentOrigin
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.contacts.booleans import IsMarketingConsentGiven
from app.use_cases.bookings.guest_booking import GuestBooking
from app.use_cases.bookings.public.managed_booking_pages import ManagedBookingPages
from app.use_cases.shared.consent_ledger import record_consent_change
from app.utilities.bookings.manage_rate_limits import ManageRateLimits

CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")
GONE_MESSAGE: str = "The guest of this booking is no longer known."
# The box's own budget: it notifies nobody, and a guest who ticks and
# unticks it must never use up the changes that cancel or move the booking.
MANAGE_CONSENT_LIMITS: ManageRateLimits = ManageRateLimits(
    key_prefix="booking-manage-consent",
    per_booking_per_minute=10,
    per_address_per_minute=30,
    per_platform_per_minute=2_000,
    refusal="Too many changes of the box; wait a moment and try again.",
)


class ChangeManagedBookingConsentUseCase(
    UseCaseContract[ManagedBookingAction, ManagedBookingView]
):
    """
    The guest ticks or unticks the marketing box on their booking's page
    (Codice privacy art. 130, GDPR art. 7). Ticking records the consent on
    the booking's contact as the guest's own: the page, this booking, the
    version of the wording the page showed and the moment; unticking takes
    it back (as easy as giving it). Ticking again keeps the first consent.
    The box is the guest's whatever the booking's state: a cancelled or
    past booking's page still shows it while its link opens. Each change
    is one atomic step on the contact as stored, counted against the box's
    own limits (`MANAGE_CONSENT_LIMITS`, never the cancellation's and the
    move's) and audited (UPDATE of the contact, no actor: the customer
    made it); a consent given or taken back is an entry of the consent
    ledger (the page, its booking and chat, the wording and its language,
    the guest's network). A STOP still wins over a ticked box until START.
    """

    def __init__(
        self,
        pages: ManagedBookingPages,
        card_repo: CustomerCardRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        consent_record_repo: ConsentRecordRepoContract,
    ) -> None:
        self._consent_record_repo: ConsentRecordRepoContract = consent_record_repo
        self._pages: ManagedBookingPages = pages
        self._card_repo: CustomerCardRepoContract = card_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ManagedBookingAction) -> ManagedBookingView:
        """
        Raises:
            ValidationFailedError: the box's state or wording is missing.
            NotFoundError: the link's booking changed, or its guest is gone.
            ConflictError: the guest's data was erased.
        """

        is_given: IsMarketingConsentGiven | None = input_data.marketing_consent
        text: MarketingConsentText | None = input_data.consent_text
        if is_given is None or text is None:
            raise ValidationFailedError("Say whether the box is ticked, and its text.")

        self._pages.refuse_too_frequent(input_data, MANAGE_CONSENT_LIMITS)
        guest_booking: GuestBooking = self._pages.current(input_data.claims)
        booking: BookingDocument = guest_booking.booking
        now: Microseconds = self._wall_clock.now_unix()

        consent_before: list[MarketingConsent | None] = []

        def change(contact: ContactDocument) -> None:
            if contact.erased_at is not None:
                raise ConflictError("The guest's data was erased.")

            consent: MarketingConsent | None = contact.marketing_consent
            consent_before.append(consent)
            if is_given and not contact.has_marketing_consent:
                contact.marketing_consent = MarketingConsent(
                    given_at=now,
                    source=MarketingConsentSource.BOOKING_PAGE,
                    text_version=text,
                    booking_id=booking.id,
                )
            elif not is_given and consent is not None:
                contact.marketing_consent = consent.withdrawn(
                    now, MarketingConsentWithdrawal.BOOKING_PAGE
                )

        changed: ContactDocument | None = self._card_repo.change_card(
            booking.business_id, booking.contact_id, change
        )
        if changed is None:
            raise NotFoundError(GONE_MESSAGE)

        record_consent_change(
            self._consent_record_repo,
            changed,
            consent_before[-1],
            changed.marketing_consent,
            ConsentOrigin(
                source=ConsentEventSource.BOOKING_PAGE,
                channel=booking.source_channel,
                # The page shows the box in the guest's language.
                language=booking.language or guest_booking.business.default_language,
                booking_id=booking.id,
                client_ip_address=input_data.client_ip_address,
            ),
            now,
        )

        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=booking.business_id,
                action=AuditAction.UPDATE,
                entity=CONTACT_ENTITY,
                entity_id=AuditEntityReference(str(changed.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return self._pages.view(
            guest_booking, self._pages.token_for(booking, input_data.claims)
        )
