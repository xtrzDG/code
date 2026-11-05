"""What the owners are told when a payment is declined."""

from app.schemas.constants.billing import BillingNoticeKind, SubscriptionStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice


def build_payment_failed_notice(
    business: BusinessDocument,
    subscription: SubscriptionDocument,
    failed_amount: Money,
) -> BillingNotice:
    """The amount, and the end of the grace period of a past-due subscription."""

    return BillingNotice(
        kind=BillingNoticeKind.PAYMENT_FAILED,
        language=business.owner_language,
        timezone=business.timezone,
        business_name=business.name,
        amount=failed_amount,
        deadline=(
            subscription.grace_until
            if subscription.status is SubscriptionStatus.PAST_DUE
            else None
        ),
    )


def invoice_amount(invoice: InvoiceDocument) -> Money:
    """What an invoice charges (a declined charge's renewal invoice)."""

    return Money(amount_minor=invoice.amount_minor, currency_code=invoice.currency_code)
