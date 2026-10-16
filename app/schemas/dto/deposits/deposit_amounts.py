"""An amount a deposit asks, and the line that asks it."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.localization.constrained_strings import CurrencyCode


class DepositAmount(ImmutableDTO):
    """What a deposit asks: `amount_minor` in minor units of `currency_code`."""

    amount_minor: DepositDueMinor
    currency_code: CurrencyCode


class IssuedDepositLine(ImmutableDTO):
    """
    The payment line send_payment_link issued in a turn: the server's text
    with the amount and the link, added under the assistant's reply as it
    is, and the amount the reply guard holds the reply's own words to.
    """

    request_id: DepositRequestId
    line: MessageText
    amount: DepositAmount
