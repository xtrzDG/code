"""The deposit a booking or a banquet request carries, as its row shows it."""

from app.schemas.domain.deposits import BookingDeposit
from app.schemas.dto.deposits.deposit_views import BookingDepositView


def deposit_row_view(deposit: BookingDeposit | None) -> BookingDepositView | None:
    if deposit is None:
        return None

    return BookingDepositView(
        request_id=deposit.request_id,
        status=deposit.status,
        amount_minor=deposit.amount_minor,
        currency_code=deposit.currency_code,
        hold_expires_at=deposit.hold_expires_at,
    )
