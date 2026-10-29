"""
A banquet request's side of its deposit: the summary it carries for the
cabinet, written when the deposit is asked and kept in step when it is
paid or lapses (a newer deposit's summary is never overwritten by an
older one's).
"""

from typed_time_provider import Microseconds

from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.deposits import DepositRequestDocument
from app.utilities.deposits.booking_deposit_state import summarize


def show_lead_deposit(
    lead: LeadDocument, request: DepositRequestDocument, now: Microseconds
) -> LeadDocument:
    """The banquet request with the summary of the deposit just asked."""

    lead.deposit = summarize(request)
    lead.updated_at = now
    return lead


def follow_lead_deposit(
    lead: LeadDocument, request: DepositRequestDocument, now: Microseconds
) -> LeadDocument | None:
    """
    The banquet request with this deposit's new state; None when it shows
    no deposit or another one.
    """

    if lead.deposit is None or lead.deposit.request_id != request.id:
        return None

    return show_lead_deposit(lead, request, now)
