"""When an owner is asked to invite another business."""

from app.schemas.typings.insights.constrained_integers import PeriodItemCount

# The Overview's invitation card shows from the business's tenth booking:
# by then the owner has seen the assistant work and has a story to tell.
INVITE_CARD_MIN_BOOKINGS: PeriodItemCount = PeriodItemCount(10)


def is_invite_card_due(bookings_made: PeriodItemCount) -> bool:
    return int(bookings_made) >= int(INVITE_CARD_MIN_BOOKINGS)
