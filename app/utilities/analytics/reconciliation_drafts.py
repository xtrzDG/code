"""
Product events derived from the stored records: what the daily
reconciliation adds when a step was never recorded (data from before
analytics, demo data, a write that failed). Once-only steps keep the ids
the live recording gives them, so nothing is stored twice; the billing
state is corrected only where the events disagree with the subscription.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName, ProductEventSource
from app.schemas.constants.billing import (
    InvoiceKind,
    InvoiceStatus,
    SubscriptionStatus,
)
from app.schemas.constants.channels import ChannelStatus
from app.schemas.domain.billing import InvoiceDocument, SubscriptionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.product_events import (
    ProductEventDocument,
    ProductEventProperties,
)
from app.schemas.domain.setup import ActivationEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.analytics.billing_event_drafts import (
    billing_event,
    monthly_recurring_amount,
)
from app.utilities.analytics.mrr_math import RevenueState, apply_step
from app.utilities.analytics.product_event_drafts import (
    business_created_event,
    channel_connected_events,
    milestone_event,
)

RECONCILED: ProductEventSource = ProductEventSource.RECONCILIATION


def reconciled(draft: ProductEventDraft) -> ProductEventDraft:
    return draft.model_copy(update={"source": RECONCILED})


def sign_up_drafts(users: Sequence[UserDocument]) -> list[ProductEventDraft]:
    """The sign-up of every account (admins left out), when it was made."""

    return [
        ProductEventDraft(
            name=ProductEventName.SIGNED_UP,
            user_id=user.id,
            properties=ProductEventProperties(login_method=user.login_method),
            occurred_at=user.created_at,
            source=RECONCILED,
        )
        for user in users
        if not user.is_platform_admin
    ]


def business_drafts(
    business: BusinessDocument,
    owner_id: UserId | None,
    milestones: Sequence[ActivationEventDocument],
    channels: Sequence[ChannelDocument],
    subscription: SubscriptionDocument | None,
) -> list[ProductEventDraft]:
    """The once-only steps a business's records prove happened."""

    drafts: list[ProductEventDraft] = []
    if owner_id is not None:
        drafts.append(business_created_event(business, owner_id))

    drafts.extend(
        milestone_event(business.id, milestone.kind, milestone.occurred_at)
        for milestone in milestones
    )
    for channel in channels:
        if channel.status is ChannelStatus.CONNECTED:
            drafts.extend(
                channel_connected_events(
                    None, business.id, channel.kind, channel.created_at
                )
            )

    if subscription is not None and subscription.trial_ends_at is not None:
        drafts.append(
            billing_event(
                ProductEventName.TRIAL_STARTED,
                subscription,
                occurred_at=subscription.period_start
                if subscription.status is SubscriptionStatus.TRIALING
                else subscription.created_at,
            )
        )

    return [reconciled(draft) for draft in drafts]


def is_paying(
    subscription: SubscriptionDocument,
    invoices: Sequence[InvoiceDocument],
    now: Microseconds,
) -> bool:
    """
    The business pays: an ACTIVE subscription, or one PAST_DUE within its
    grace that has paid a service period before (a trial that ended unpaid
    never paid, and a grace that ran out is churn).
    """

    if subscription.status is SubscriptionStatus.ACTIVE:
        return True

    if subscription.status is not SubscriptionStatus.PAST_DUE:
        return False

    in_grace: bool = subscription.grace_until is not None and int(
        subscription.grace_until
    ) > int(now)
    return in_grace and any(
        invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status is InvoiceStatus.PAID
        for invoice in invoices
    )


def billing_corrections(
    subscription: SubscriptionDocument,
    invoices: Sequence[InvoiceDocument],
    events: Sequence[ProductEventDocument],
    now: Microseconds,
) -> list[ProductEventDraft]:
    """
    The billing step that makes the replayed events agree with the
    subscription as stored: SUBSCRIBED (from the first paid period when no
    step was ever recorded), PLAN_CHANGED or CANCELLED; none when they agree.
    """

    state = RevenueState()
    last_at: int = 0
    for event in sorted(events, key=lambda item: (int(item.occurred_at), item.id)):
        amount = event.properties.monthly_amount
        apply_step(state, event.name, 0 if amount is None else int(amount))
        last_at = max(last_at, int(event.occurred_at))

    paying: bool = is_paying(subscription, invoices, now)
    monthly: int = int(monthly_recurring_amount(subscription))
    name: ProductEventName | None = None
    if paying and not state.is_paying:
        name = ProductEventName.SUBSCRIBED
    elif paying and state.amount != monthly:
        name = ProductEventName.PLAN_CHANGED
    elif not paying and state.is_paying:
        name = ProductEventName.CANCELLED

    if name is None:
        return []

    paid_starts: list[int] = [
        int(invoice.period_start)
        for invoice in invoices
        if invoice.kind is InvoiceKind.SERVICE_PERIOD
        and invoice.status is InvoiceStatus.PAID
    ]
    first_paid: int = min(paid_starts, default=int(subscription.updated_at))
    when: int = (
        first_paid
        if name is ProductEventName.SUBSCRIBED and not events
        else int(subscription.updated_at)
    )
    return [
        reconciled(
            billing_event(
                name, subscription, occurred_at=Microseconds(max(when, last_at + 1))
            )
        )
    ]
