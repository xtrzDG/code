"""Stripe test clients and checkout requests for the payment tests."""

import httpx
from typed_time_provider import Microseconds

from app.clients.stripe.stripe_client import (
    StripeClient,
)
from app.schemas.constants.payments import (
    PaymentOrderPurpose,
    PaymentProvider,
)
from app.schemas.dto.billing import Money
from app.schemas.dto.payments import (
    PaymentCheckoutRequest,
    RecurringCharge,
)
from app.schemas.typings.billing.constrained_integers import (
    BillingIntervalMonths,
    MoneyAmountMinor,
)
from app.schemas.typings.billing.constrained_strings import AutoDebitStartDate
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformSecret
from tests.billing.billing_settings import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from tests.billing.stripe_sandbox import StripeSandbox

NOW_SECONDS: int = 1_790_845_200
DAY_SECONDS: int = 86_400


def build_stripe_client(
    handler: httpx.MockTransport | None = None, sandbox: StripeSandbox | None = None
) -> StripeClient:
    return StripeClient(
        secret_key=PlatformSecret(STRIPE_SECRET_KEY),
        webhook_secret=PlatformSecret(STRIPE_WEBHOOK_SECRET),
        transport=handler or httpx.MockTransport((sandbox or StripeSandbox()).handle),
    )


def euros(amount_minor: int) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(amount_minor), currency_code=CurrencyCode("EUR")
    )


def checkout_request(
    starts_in_seconds: int,
    purpose: PaymentOrderPurpose = PaymentOrderPurpose.CHECKOUT,
    interval_months: int = 1,
) -> PaymentCheckoutRequest:
    return PaymentCheckoutRequest(
        provider=PaymentProvider.STRIPE,
        payment_order_id=PaymentOrderId(),
        amount=euros(0 if purpose is PaymentOrderPurpose.CARD_SETUP else 31900),
        description=InvoiceDescription("Call and message handling service"),
        recurring_charge=RecurringCharge(
            amount=euros(17500),
            interval_months=BillingIntervalMonths(interval_months),
            start_date=AutoDebitStartDate("2026-11-15"),
            starts_at=Microseconds((NOW_SECONDS + starts_in_seconds) * 1_000_000),
        ),
        language=LanguageTag("de-AT"),
        purpose=purpose,
    )
