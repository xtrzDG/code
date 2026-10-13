"""A deposit request as staff see it."""

from app.schemas.domain.deposits import DepositRequestDocument, DepositSettingsDocument
from app.schemas.dto.deposits.deposit_views import DepositRequestView
from app.utilities.deposits.payment_pages import issued_page


def build_request_view(
    request: DepositRequestDocument, settings: DepositSettingsDocument | None
) -> DepositRequestView:
    page = issued_page(settings, request.payment_link_id)
    return DepositRequestView(
        id=request.id,
        subject=request.subject,
        booking_id=request.booking_id,
        lead_id=request.lead_id,
        contact_id=request.contact_id,
        source_channel=request.source_channel,
        status=request.status,
        amount_minor=request.amount_minor,
        currency_code=request.currency_code,
        reference=request.reference,
        payment_link_label=None if page is None else page.label,
        requested_at=request.requested_at,
        hold_expires_at=request.hold_expires_at,
        reminder_sent_at=request.reminder_sent_at,
        paid_at=request.paid_at,
        marked_paid_by=request.marked_paid_by,
        cancelled_at=request.cancelled_at,
        settled_at=request.settled_at,
    )
