"""The card on file as the billing page shows it, and when it may change."""

from typed_time_provider import Microseconds

from app.contracts.payment_methods import PaymentProviderRegistryContract
from app.schemas.constants.billing import InvoiceKind, SubscriptionStatus
from app.schemas.constants.payments import PaymentProvider
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payment_methods import PaymentMethodSummary
from app.schemas.dto.payment_methods import PaymentCardView
from app.schemas.typings.billing.constrained_integers import TrialCardPromptDayOffset
from app.use_cases.shared.billing_records import list_open_invoices
from app.utilities.billing.billing_periods import add_local_days

# "Save card" is asked for from day 10 of a trial (nine full days in).
TRIAL_CARD_PROMPT_DAY_OFFSET: TrialCardPromptDayOffset = TrialCardPromptDayOffset(9)


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
    A card is saved or replaced in a trial (its page pays a setup fee the
    trial owes), in a paid subscription without unpaid bills, and while a
    declined automatic charge is retried (past due with the charges still
    running: the retries and the next charges use the new card). Another
    unpaid bill is paid instead (its checkout saves the card too).
    """

    if subscription is None:
        return False

    open_invoices: list[InvoiceDocument] = list_open_invoices(invoices)
    match subscription.status:
        case SubscriptionStatus.TRIALING:
            return all(
                invoice.kind is InvoiceKind.SETUP_FEE for invoice in open_invoices
            )
        case SubscriptionStatus.ACTIVE:
            return open_invoices == []
        case SubscriptionStatus.PAST_DUE:
            return subscription.provider_reference is not None
        case _:
            return False


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
        subscription.period_start,
        int(TRIAL_CARD_PROMPT_DAY_OFFSET),
        business.timezone,
    )
    return now >= prompt_from
