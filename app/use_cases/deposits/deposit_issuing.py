"""
Asking a deposit: the request (amount, reference, page, hold and the
reminder halfway through), the booking held for it, and the payment line
the customer receives (built again from the request when it is sent once
more, so the amount and the reference never change).
"""

from dataclasses import dataclass
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.deposit_repositories import (
    DepositRequestRepoContract,
)
from app.schemas.constants.deposits import (
    DepositRefusalCode,
    DepositSubject,
    PaymentLinkOutcome,
)
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import (
    DepositRequestDocument,
    DepositSettingsDocument,
    PaymentLink,
)
from app.schemas.dto.deposits.deposit_amounts import DepositAmount, IssuedDepositLine
from app.schemas.dto.deposits.payment_link_requests import (
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
)
from app.schemas.typings.deposits.strings import DepositHoldEndText
from app.use_cases.deposits.deposit_quotes import QuotedDeposit
from app.use_cases.deposits.payment_lines import LineValues, PaymentLines, chosen_link
from app.utilities.deposits.booking_deposit_state import held_status, show_deposit
from app.utilities.deposits.deposit_keys import new_deposit_reference
from app.utilities.deposits.deposit_line_texts import (
    DEPOSIT_BANQUET_LINE,
    DEPOSIT_BOOKING_LINE,
)
from app.utilities.deposits.deposit_refusals import deposit_refusal
from app.utilities.deposits.deposit_times import hold_end_text, minutes_later
from app.utilities.deposits.lead_deposit_state import show_lead_deposit
from app.utilities.scheduling.zoned_time import load_time_zone

MICROSECONDS_PER_SECOND: int = 1_000_000
# A hold this long or longer gets one reminder, halfway through.
SHORTEST_REMINDED_HOLD_MINUTES: int = 30


@dataclass(frozen=True)
class DepositIssuing:
    request_repo: DepositRequestRepoContract
    booking_repo: BookingRepoContract
    lead_repo: LeadRepoContract
    lines: PaymentLines

    def issue(
        self,
        settings: DepositSettingsDocument,
        subject: BookingDocument | LeadDocument,
        quoted: QuotedDeposit,
        command: SendPaymentLinkCommand,
        now: Microseconds,
    ) -> DepositRequestDocument:
        """
        Store a new request, hold the booking for it or show it on the
        banquet request (under the business lock). Raises
        ValidationFailedError when there is no page to pay on.
        """

        if quoted.amount is None or quoted.policy is None:
            raise ValueError("Only a quoted deposit is issued.")

        link: PaymentLink | None = chosen_link(settings, quoted.policy.payment_link_id)
        if link is None:
            raise deposit_refusal(
                DepositRefusalCode.NO_PAYMENT_LINK,
                "This business has no payment page for the deposit yet.",
            )

        hold_minutes: int = int(settings.hold_minutes)
        hold_end: Microseconds = minutes_later(now, hold_minutes)
        if isinstance(subject, BookingDocument):
            starts_at = Microseconds(int(subject.starts_at) * MICROSECONDS_PER_SECOND)
            hold_end = Microseconds(min(int(hold_end), int(starts_at)))

        request = DepositRequestDocument(
            business_id=subject.business_id,
            subject=subject_of(subject),
            booking_id=subject.id if isinstance(subject, BookingDocument) else None,
            lead_id=subject.id if isinstance(subject, LeadDocument) else None,
            contact_id=subject.contact_id,
            conversation_id=command.conversation_id,
            source_channel=command.source_channel,
            language=command.language,
            amount_minor=quoted.amount.amount_minor,
            currency_code=quoted.amount.currency_code,
            reference=new_deposit_reference(),
            payment_link_id=link.id,
            requested_at=now,
            hold_expires_at=hold_end,
            reminder_due_at=(
                minutes_later(now, hold_minutes // 2)
                if hold_minutes >= SHORTEST_REMINDED_HOLD_MINUTES
                else None
            ),
            is_sandbox=command.is_sandbox,
            created_at=now,
            updated_at=now,
        )
        self.request_repo.save(request)
        if isinstance(subject, BookingDocument):
            self.booking_repo.update(
                subject.business_id,
                subject.id,
                lambda booking: hold_booking(booking, request, now),
            )
        else:
            self.lead_repo.update(
                subject.business_id,
                subject.id,
                lambda lead: show_lead_deposit(lead, request, now),
            )
        return request

    def receipt(
        self,
        business: BusinessDocument,
        settings: DepositSettingsDocument,
        request: DepositRequestDocument,
        now: Microseconds,
    ) -> PaymentLinkReceipt:
        """The payment line of a waiting request, in its customer's language."""

        link: PaymentLink | None = next(
            (
                link
                for link in settings.payment_links
                if link.id == request.payment_link_id
            ),
            None,
        )
        if link is None:
            raise deposit_refusal(
                DepositRefusalCode.NO_PAYMENT_LINK,
                "The payment page of this deposit was removed.",
            )

        amount = DepositAmount(
            amount_minor=request.amount_minor, currency_code=request.currency_code
        )
        template = (
            DEPOSIT_BOOKING_LINE
            if request.subject is DepositSubject.BOOKING
            else DEPOSIT_BANQUET_LINE
        )
        zone: ZoneInfo = load_time_zone(business.timezone)
        until: DepositHoldEndText = hold_end_text(
            request.hold_expires_at, now, zone, request.language
        )
        amount_text = self.lines.amount_text(template, amount, request.language)
        line = self.lines.line(
            template,
            LineValues(
                amount=amount_text,
                link=self.lines.url(link, amount, request.reference),
                until=until,
                reference=request.reference,
            ),
            request.language,
        )
        return PaymentLinkReceipt(
            outcome=PaymentLinkOutcome.SENT,
            subject=request.subject,
            booking_id=request.booking_id,
            lead_id=request.lead_id,
            amount=amount,
            amount_text=amount_text,
            held_until_text=until,
            reference=request.reference,
            issued=IssuedDepositLine(request_id=request.id, line=line, amount=amount),
        )


def subject_of(subject: BookingDocument | LeadDocument) -> DepositSubject:
    if isinstance(subject, BookingDocument):
        return DepositSubject.BOOKING

    return DepositSubject.BANQUET


def hold_booking(
    booking: BookingDocument, request: DepositRequestDocument, now: Microseconds
) -> BookingDocument:
    """The booking keeps its place, waiting for the deposit."""

    booking.status = held_status()
    booking.last_status_change = None
    return show_deposit(booking, request, now)
