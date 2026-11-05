"""How well the business knows a customer: new, returning, visited, regular."""

from app.schemas.constants.customers import CustomerStanding
from app.schemas.typings.contacts.constrained_integers import (
    ContactConversationCount,
    ContactVisitCount,
)

# Visits from which a customer is a regular ("Regular customer · 4 visits").
REGULAR_VISITS: int = 2


def standing_of(
    visit_count: ContactVisitCount,
    conversation_count: ContactConversationCount,
    call_count: int = 0,
) -> CustomerStanding:
    """
    REGULAR from two visits, VISITED after one; without a visit RETURNING
    when the customer wrote or called more than once, else NEW.
    """

    if int(visit_count) >= REGULAR_VISITS:
        return CustomerStanding.REGULAR

    if int(visit_count) == 1:
        return CustomerStanding.VISITED

    if int(conversation_count) + call_count > 1:
        return CustomerStanding.RETURNING

    return CustomerStanding.NEW
