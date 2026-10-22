"""Open a payment order at its provider: a checkout or a card setup page."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.contracts.billing import (
    PaymentGatewayAdapterContract,
    PaymentOrderRepoContract,
)
from app.schemas.constants.payments import PaymentOrderPurpose, PaymentProvider
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    PaymentCheckoutSession,
    RecurringCharge,
)
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from app.schemas.typings.billing.prefixed_id import InvoiceId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.billing.billing_periods import (
    get_interval_months,
    to_local_calendar_day,
)


class PaymentOrderOpening(ImmutableDTO):
    """
    What a new payment order charges now (`amount` for `invoice_ids`;
    nothing for a card setup) and the automatic charges of `recurring`
    that follow from `charges_from`, at `provider`.
    """

    provider: PaymentProvider
    purpose: PaymentOrderPurpose
    invoice_ids: list[InvoiceId]
    amount: Money
    recurring: Money
    charges_from: Microseconds
    description: InvoiceDescription
    language: LanguageTag
    return_url: PaymentReturnUrl | None = None
    customer_reference: PaymentProviderReference | None = None


def open_payment_order(
    payment_gateway: PaymentGatewayAdapterContract,
    payment_order_repo: PaymentOrderRepoContract,
    business: BusinessDocument,
    subscription: SubscriptionDocument,
    opening: PaymentOrderOpening,
    now: Microseconds,
) -> tuple[PaymentOrderDocument, PaymentCheckoutSession]:
    """
    A new provider order (every attempt is its own, so a declined one can
    be tried again): its hosted page, saved with the order.

    Raises:
        ExternalServiceError: the provider is not configured or failed.
    """

    payment_order = PaymentOrderDocument(
        business_id=business.id,
        subscription_id=subscription.id,
        provider=opening.provider,
        purpose=opening.purpose,
        invoice_ids=list(opening.invoice_ids),
        amount_minor=opening.amount.amount_minor,
        currency_code=opening.amount.currency_code,
        recurring_amount_minor=opening.recurring.amount_minor,
        recurring_interval_months=get_interval_months(subscription.billing_period),
        customer_reference=opening.customer_reference,
    )
    session: PaymentCheckoutSession = payment_gateway.create_checkout(
        PaymentCheckoutRequest(
            provider=opening.provider,
            payment_order_id=payment_order.id,
            amount=opening.amount,
            description=opening.description,
            recurring_charge=RecurringCharge(
                amount=opening.recurring,
                interval_months=payment_order.recurring_interval_months,
                start_date=to_local_calendar_day(
                    opening.charges_from, business.timezone
                ),
                starts_at=opening.charges_from,
            ),
            language=opening.language,
            return_url=opening.return_url,
            purpose=opening.purpose,
            customer_reference=opening.customer_reference,
        )
    )
    payment_order.checkout_url = session.checkout_url
    payment_order.last_payment_reference = session.payment_reference
    payment_order.created_at = now
    payment_order.updated_at = now
    payment_order_repo.save(payment_order)
    return payment_order, session
