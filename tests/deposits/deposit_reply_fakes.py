"""
A send_payment_link that issues a deposit, for the conversation engine's
tests: the receipt a held booking gets (amount, held_until and the payment
line), so the tests see what reaches the customer whatever the turn did.
"""

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import DepositSubject, PaymentLinkOutcome
from app.schemas.dto.deposits.deposit_amounts import DepositAmount, IssuedDepositLine
from app.schemas.dto.deposits.payment_link_requests import (
    PaymentLinkReceipt,
    SendPaymentLinkCommand,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deposits.constrained_integers import DepositDueMinor
from app.schemas.typings.deposits.constrained_strings import DepositReference
from app.schemas.typings.deposits.prefixed_id import DepositRequestId
from app.schemas.typings.deposits.strings import DepositHoldEndText
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.localization.strings import FormattedMoneyText

PAYMENT_LINE: str = (
    "Deposit GEL 120.00: https://pay.example.com/deposit?sum=120.00&ref=DK7Q3M9X"
)


class IssuingPaymentLink(UseCaseContract[SendPaymentLinkCommand, PaymentLinkReceipt]):
    """Every call issues the same deposit, held until `held_until`."""

    def __init__(self, held_until: str = "21:00") -> None:
        self.held_until: str = held_until
        self.calls: list[SendPaymentLinkCommand] = []

    def run(self, input_data: SendPaymentLinkCommand) -> PaymentLinkReceipt:
        self.calls.append(input_data)
        amount = DepositAmount(
            amount_minor=DepositDueMinor(12000), currency_code=CurrencyCode("GEL")
        )
        return PaymentLinkReceipt(
            outcome=PaymentLinkOutcome.SENT,
            subject=DepositSubject.BOOKING,
            amount=amount,
            amount_text=FormattedMoneyText("GEL 120.00"),
            held_until_text=DepositHoldEndText(self.held_until),
            reference=DepositReference("DK7Q3M9X"),
            issued=IssuedDepositLine(
                request_id=DepositRequestId(),
                line=MessageText(PAYMENT_LINE),
                amount=amount,
            ),
        )
