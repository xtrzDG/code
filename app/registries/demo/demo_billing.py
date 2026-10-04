"""
Billing of the demo businesses: a running trial or a paid monthly
subscription, and the usage their seeded conversations and calls metered
in the current package window (the dashboard and billing pages read it).
"""

from collections.abc import Mapping, Sequence

from typed_time_provider import Microseconds

from app.contracts.registries import PlanRegistryContract
from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
    UsageKind,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.billing_profiles import (
    BillingProfileDocument,
    InvoiceLineText,
    PaymentCardSnapshot,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.dto.billing import Money, PlanDefinition
from app.schemas.typings.billing.constrained_integers import (
    CostMicroUsd,
    UsageQuantity,
)
from app.schemas.typings.billing.strings import (
    InvoiceDescription,
    PaymentProviderReference,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.invoicing.constrained_strings import (
    BillingAddressText,
    BillingLegalName,
    PaymentCardLastDigits,
    TaxpayerIdentificationNumber,
)
from app.schemas.typings.invoicing.strings import PaymentCardBrand
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.billing.billing_periods import add_calendar_months, add_local_days
from app.utilities.billing.invoicing_keys import derive_billing_profile_id

# The demo card a paid demo invoice was charged to (masked as Flitt reports it).
DEMO_CARD = PaymentCardSnapshot(
    brand=PaymentCardBrand("MASTERCARD"), last_digits=PaymentCardLastDigits("4417")
)


def price_of(plan_registry: PlanRegistryContract, business: BusinessDocument) -> Money:
    """The monthly price in the business currency when the price book has it."""

    plan: PlanDefinition = plan_registry.get(business.plan_key)
    return (
        plan_registry.find_local_monthly_price(
            business.plan_key, business.currency_code
        )
        or plan.monthly_price
    )


def trial_subscription(
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    started_at: Microseconds,
) -> SubscriptionDocument:
    """The plan's free trial, started at `started_at` (still running)."""

    price: Money = price_of(plan_registry, business)
    trial_days: int = int(plan_registry.get(business.plan_key).trial_days)
    trial_ends_at: Microseconds = add_local_days(
        started_at, trial_days, business.timezone
    )
    return SubscriptionDocument(
        business_id=business.id,
        plan_key=business.plan_key,
        billing_period=BillingPeriod.MONTHLY,
        price_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=SubscriptionStatus.TRIALING,
        trial_ends_at=trial_ends_at,
        period_start=started_at,
        period_end=trial_ends_at,
        created_at=started_at,
        updated_at=started_at,
    )


def paid_subscription(
    plan_registry: PlanRegistryContract,
    business: BusinessDocument,
    period_start: Microseconds,
    reference: str,
    invoice_lines: Mapping[str, str],
) -> tuple[SubscriptionDocument, InvoiceDocument]:
    """
    An active monthly subscription and the paid invoice of its period;
    `invoice_lines` words its line by language ("en" is the issued line).
    """

    price: Money = price_of(plan_registry, business)
    period_end: Microseconds = add_calendar_months(period_start, 1, business.timezone)
    subscription = SubscriptionDocument(
        business_id=business.id,
        plan_key=business.plan_key,
        billing_period=BillingPeriod.MONTHLY,
        price_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=SubscriptionStatus.ACTIVE,
        period_start=period_start,
        period_end=period_end,
        provider_reference=PaymentProviderReference(reference),
        created_at=period_start,
        updated_at=period_start,
    )
    invoice = InvoiceDocument(
        business_id=business.id,
        subscription_id=subscription.id,
        kind=InvoiceKind.SERVICE_PERIOD,
        description=InvoiceDescription(invoice_lines["en"]),
        line_texts=[
            InvoiceLineText(
                language=LanguageTag(language), text=InvoiceDescription(text)
            )
            for language, text in invoice_lines.items()
        ],
        amount_minor=price.amount_minor,
        currency_code=price.currency_code,
        status=InvoiceStatus.PAID,
        period_start=period_start,
        period_end=period_end,
        provider_reference=PaymentProviderReference(f"{reference}-1"),
        paid_at=period_start,
        payment_card=DEMO_CARD,
        created_at=period_start,
        updated_at=period_start,
    )
    return subscription, invoice


def billing_details(
    business: BusinessDocument,
    legal_name: str,
    tax_id: str,
    address: str,
    billing_email: str,
    saved_at: Microseconds,
) -> BillingProfileDocument:
    """What the owner entered in "Billing details", in the business country."""

    return BillingProfileDocument(
        id=derive_billing_profile_id(business.id),
        business_id=business.id,
        legal_name=BillingLegalName(legal_name),
        tax_id=TaxpayerIdentificationNumber(tax_id),
        address=BillingAddressText(address),
        billing_email=EmailAddress(billing_email),
        country_code=business.country_code,
        created_at=saved_at,
        updated_at=saved_at,
    )


def metered_usage(
    business: BusinessDocument,
    conversations: Sequence[ConversationDocument],
    messages: Sequence[MessageDocument],
    calls: Sequence[CallDocument],
    since: Microseconds,
) -> list[UsageEventDocument]:
    """
    What the seeded conversations and calls metered since `since`, as the
    engine meters them: one dialog per customer conversation the assistant
    answered (a call counts in minutes instead, a sandbox not at all), and
    each call's seconds with its provider cost. So the package usage the
    cabinet and the admin show is the usage of the conversations they list.
    """

    answered: set[ConversationId] = {
        message.conversation_id
        for message in messages
        if message.author is MessageAuthor.ASSISTANT
    }
    events: list[UsageEventDocument] = [
        UsageEventDocument(
            business_id=business.id,
            conversation_id=conversation.id,
            kind=UsageKind.DIALOG,
            quantity=UsageQuantity(1),
            cost_micro_usd=CostMicroUsd(0),
            occurred_at=conversation.created_at,
            created_at=conversation.created_at,
            updated_at=conversation.created_at,
        )
        for conversation in conversations
        if conversation.id in answered
        and conversation.channel is not ChannelKind.PHONE
        and not conversation.is_sandbox
        and int(conversation.created_at) >= int(since)
    ]
    events.extend(
        UsageEventDocument(
            business_id=business.id,
            conversation_id=call.conversation_id,
            kind=UsageKind.VOICE_SECONDS,
            quantity=UsageQuantity(int(call.duration_seconds)),
            cost_micro_usd=call.cost_micro_usd,
            occurred_at=call.started_at,
            created_at=call.updated_at,
            updated_at=call.updated_at,
        )
        for call in calls
        if int(call.started_at) >= int(since) and int(call.duration_seconds) > 0
    )
    return sorted(events, key=lambda event: int(event.occurred_at))
