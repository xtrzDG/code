"""What the platform team granted a client, as its admin page shows it."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.dto.admin_actions import ClientAccountView, ClientDiscountView
from app.schemas.dto.billing import Money
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.utilities.billing.billing_credit_ledger import credit_balance


def build_client_account(
    subscription: SubscriptionDocument | None,
    credits: Sequence[BillingCreditDocument],
    invoices: Sequence[InvoiceDocument],
    now: Microseconds,
) -> ClientAccountView | None:
    """
    The trial's end (while it is a trial), the discount (active until it
    ends), the credit left in the subscription's currency and the waived
    setup fee; None without a subscription.
    """

    if subscription is None:
        return None

    discount = subscription.discount
    return ClientAccountView(
        trial_ends_at=(
            subscription.trial_ends_at
            if subscription.status is SubscriptionStatus.TRIALING
            else None
        ),
        discount=(
            None
            if discount is None
            else ClientDiscountView(
                percent=discount.percent,
                ends_at=discount.ends_at,
                is_active=int(now) < int(discount.ends_at),
            )
        ),
        credit_balance=Money(
            amount_minor=MoneyAmountMinor(
                credit_balance(credits, invoices, subscription.currency_code)
            ),
            currency_code=subscription.currency_code,
        ),
        is_setup_fee_waived=subscription.is_setup_fee_waived,
    )
