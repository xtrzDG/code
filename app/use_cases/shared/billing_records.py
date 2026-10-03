"""Lookups over subscriptions and invoices shared by the billing use cases."""

from typed_time_provider import Microseconds

from app.contracts.repositories.billing_repositories import (
    InvoiceRepoContract,
    SubscriptionRepoContract,
)
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.dto.billing import Money
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId

OPEN_INVOICE_STATUSES: frozenset[InvoiceStatus] = frozenset(
    {InvoiceStatus.ISSUED, InvoiceStatus.FAILED}
)


def is_superseded_period(
    invoice: InvoiceDocument,
    paid_periods: list[InvoiceDocument],
    subscription: SubscriptionDocument,
) -> bool:
    """
    A service period that must not be booked as paid: it overlaps a period
    already paid (a second checkout page for nearly the same month), or it
    was voided because a free trial covers it.
    """

    if invoice.kind is not InvoiceKind.SERVICE_PERIOD:
        return False

    if any(
        invoice.period_start < paid.period_end
        and paid.period_start < invoice.period_end
        for paid in paid_periods
        if paid.id != invoice.id
    ):
        return True

    return (
        invoice.status is InvoiceStatus.VOID
        and subscription.trial_ends_at is not None
        and invoice.period_start < subscription.trial_ends_at
    )


def find_current_subscription(
    subscription_repo: SubscriptionRepoContract,
    business_id: BusinessId,
) -> SubscriptionDocument | None:
    """The most recently created subscription of a business, if any."""

    subscriptions: list[SubscriptionDocument] = subscription_repo.list_by_business(
        business_id
    )
    if subscriptions == []:
        return None

    return max(
        subscriptions,
        key=lambda subscription: (subscription.created_at, subscription.period_start),
    )


def require_current_subscription(
    subscription_repo: SubscriptionRepoContract,
    business_id: BusinessId,
) -> SubscriptionDocument:
    """
    Raises:
        NotFoundError: the business has no subscription (no trial started).
    """

    subscription: SubscriptionDocument | None = find_current_subscription(
        subscription_repo,
        business_id,
    )
    if subscription is None:
        raise NotFoundError("The business has no subscription; start the trial first.")

    return subscription


def is_service_paid_for(
    subscription: SubscriptionDocument | None,
    now: Microseconds,
) -> bool:
    """
    True while the business is entitled to the assistant (concept section 9):
    a running trial, an active subscription, a missed payment still within
    its grace, or a cancelled subscription inside the period already paid.
    """

    if subscription is None:
        return False

    match subscription.status:
        case SubscriptionStatus.INCOMPLETE:
            return False
        case SubscriptionStatus.ACTIVE:
            return True
        case SubscriptionStatus.TRIALING:
            return (
                subscription.trial_ends_at is None or now < subscription.trial_ends_at
            )
        case SubscriptionStatus.PAST_DUE:
            return subscription.grace_until is None or now < subscription.grace_until
        case SubscriptionStatus.CANCELLED:
            return now < subscription.period_end


def is_trial_available(subscriptions: list[SubscriptionDocument]) -> bool:
    """
    The free trial is offered once per business: while it has no
    subscription, or only ones chosen without a trial and never paid.
    """

    return all(
        subscription.status is SubscriptionStatus.INCOMPLETE
        and subscription.trial_ends_at is None
        for subscription in subscriptions
    )


def list_subscription_invoices(
    invoice_repo: InvoiceRepoContract,
    subscription: SubscriptionDocument,
) -> list[InvoiceDocument]:
    """Invoices of one subscription, oldest service period first."""

    return sorted(
        (
            invoice
            for invoice in invoice_repo.list_by_business(subscription.business_id)
            if invoice.subscription_id == subscription.id
        ),
        key=lambda invoice: (invoice.period_start, invoice.created_at),
    )


def list_open_invoices(invoices: list[InvoiceDocument]) -> list[InvoiceDocument]:
    """Invoices still to pay: issued, or failed and waiting for a new attempt."""

    return [invoice for invoice in invoices if invoice.status in OPEN_INVOICE_STATUSES]


def find_paid_period_invoice(
    invoices: list[InvoiceDocument],
    period_start: Microseconds,
) -> InvoiceDocument | None:
    """A paid service-period invoice whose period starts exactly then."""

    for invoice in invoices:
        if (
            invoice.kind is InvoiceKind.SERVICE_PERIOD
            and invoice.status is InvoiceStatus.PAID
            and invoice.period_start == period_start
        ):
            return invoice

    return None


def find_covering_paid_invoice(
    invoices: list[InvoiceDocument],
    now: Microseconds,
) -> InvoiceDocument | None:
    """The paid service-period invoice whose period contains `now`."""

    covering: list[InvoiceDocument] = [
        invoice
        for invoice in invoices
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status is InvoiceStatus.PAID
        and invoice.period_start <= now < invoice.period_end
    ]
    if covering == []:
        return None

    return max(covering, key=lambda invoice: invoice.period_end)


def find_next_period_start(
    subscription: SubscriptionDocument,
    invoices: list[InvoiceDocument],
) -> Microseconds:
    """
    Start of the next unpaid service period: the end of the current period
    or of the last period already paid ahead, whichever is later.
    """

    paid_period_ends: list[Microseconds] = [
        invoice.period_end
        for invoice in invoices
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status is InvoiceStatus.PAID
    ]
    return max([subscription.period_end, *paid_period_ends])


def advance_to_paid_periods(
    subscription: SubscriptionDocument,
    invoices: list[InvoiceDocument],
    now: Microseconds,
) -> bool:
    """
    Move a subscription whose period has ended into the following periods
    that were paid ahead; return True when the period moved.
    """

    has_moved: bool = False
    while subscription.period_end <= now:
        paid_invoice: InvoiceDocument | None = find_paid_period_invoice(
            invoices,
            subscription.period_end,
        )
        if paid_invoice is None or paid_invoice.period_end <= paid_invoice.period_start:
            break

        subscription.period_start = paid_invoice.period_start
        subscription.period_end = paid_invoice.period_end
        has_moved = True

    return has_moved


def sum_invoice_amounts(invoices: list[InvoiceDocument]) -> Money:
    """
    Total of invoices in one currency.

    Raises:
        ConflictError: no invoices, or invoices in different currencies.
    """

    if invoices == []:
        raise ConflictError("There is nothing to pay.")

    currency_codes = {invoice.currency_code for invoice in invoices}
    if len(currency_codes) != 1:
        raise ConflictError("Open invoices are in different currencies.")

    return Money(
        amount_minor=MoneyAmountMinor(
            sum(int(invoice.amount_minor) for invoice in invoices)
        ),
        currency_code=invoices[0].currency_code,
    )
