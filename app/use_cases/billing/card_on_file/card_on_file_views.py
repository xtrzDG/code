"""The card on file as the billing page shows it, and when it may change."""

from typed_time_provider import Microseconds

from app.contracts.payment_methods import PaymentProviderRegistryContract
from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.dto.payment_methods import PaymentCardView
from app.use_cases.shared.billing_records import list_open_invoices
from app.utilities.billing.billing_periods import add_local_days

# "Save card" is asked for from day 10 of a trial (nine full days in).
TRIAL_CARD_PROMPT_DAY_OFFSET: int = 9
CARD_SETUP_STATUSES: frozenset[SubscriptionStatus] = frozenset(
    {SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE}
)


def select_card_provider(
    registry: PaymentProviderRegistryContract,
    business: BusinessDocument,
    subscription: SubscriptionDocument | None,
) -> PaymentProvider:
    """Who charges the card: the running schedule's provider, else the region's."""

    if (
        subscription is not None
        and subscription.provider_reference is not None
        and subscription.payment_provider is not None
    ):
        return subscription.payment_provider

    return registry.select(business.country_code)


def build_card_view(summary: PaymentMethodSummary | None) -> PaymentCardView | None:
    if summary is None:
        return None

    return PaymentCardView(
        brand=summary.brand,
        last_digits=summary.last_digits,
        expiry_month=summary.expiry_month,
        expiry_year=summary.expiry_year,
        saved_at=summary.saved_at,
    )


def can_save_card(
    subscription: SubscriptionDocument | None, invoices: list[InvoiceDocument]
) -> bool:
    """
    A card is saved or replaced in a trial or a paid subscription without
    unpaid bills; an unpaid bill is paid instead (its checkout saves the
    card too).
    """

    return (
        subscription is not None
        and subscription.status in CARD_SETUP_STATUSES
        and list_open_invoices(invoices) == []
    )


def is_trial_card_prompt_due(
    subscription: SubscriptionDocument | None,
    business: BusinessDocument,
    now: Microseconds,
) -> bool:
    """From day 10 of a trial that has no card for its first charge."""

    if (
        subscription is None
        or subscription.status is not SubscriptionStatus.TRIALING
        or subscription.trial_ends_at is None
        or subscription.provider_reference is not None
        or now >= subscription.trial_ends_at
    ):
        return False

    prompt_from: Microseconds = add_local_days(
        subscription.period_start, TRIAL_CARD_PROMPT_DAY_OFFSET, business.timezone
    )
    return now >= prompt_from
