"""
The founder's churn view from the steps of subscriptions' lives: the
period's cancellations by reason, the offers taken instead, pauses, the
win-back messages and who came back after one.
"""

from collections import Counter
from collections.abc import Collection, Sequence

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    SubscriptionEventKind,
)
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.dto.analytics.churn_views import (
    ChurnComment,
    ChurnReasonRow,
    ChurnView,
    RetentionOfferRow,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.subscription_lifecycle.constrained_integers import (
    CancellationCount,
    SubscriptionStepCount,
)

MAX_COMMENTS: int = 10
# A subscription opened again: a new trial or a paid subscription.
RETURN_EVENTS: frozenset[ProductEventName] = frozenset(
    {ProductEventName.SUBSCRIBED, ProductEventName.TRIAL_STARTED}
)


def build_churn(
    steps: Sequence[SubscriptionEventDocument],
    billing: Sequence[ProductEventDocument],
    in_scope: Collection[BusinessId],
) -> ChurnView:
    """
    `steps`: the period's lifecycle steps of every kind; `billing`: the
    billing product events (any time) a return is read from; only the
    businesses in scope count.
    """

    scoped: list[SubscriptionEventDocument] = [
        step for step in steps if step.business_id in in_scope
    ]

    def of_kind(kind: SubscriptionEventKind) -> list[SubscriptionEventDocument]:
        return [step for step in scoped if step.kind is kind]

    cancelled = of_kind(SubscriptionEventKind.CANCELLED)
    accepted = of_kind(SubscriptionEventKind.OFFER_ACCEPTED)
    win_backs = of_kind(SubscriptionEventKind.WIN_BACK_SENT)
    return ChurnView(
        cancellations=CancellationCount(len(cancelled)),
        reasons=reason_rows(cancelled, accepted),
        offers=offer_rows(accepted),
        pauses_scheduled=SubscriptionStepCount(
            len(of_kind(SubscriptionEventKind.PAUSE_SCHEDULED))
        ),
        pauses_ended=SubscriptionStepCount(len(of_kind(SubscriptionEventKind.RESUMED))),
        win_back_sent=SubscriptionStepCount(len(win_backs)),
        returned_after_win_back=SubscriptionStepCount(
            count_returns(win_backs, billing)
        ),
        comments=comments(cancelled),
    )


def reason_rows(
    cancelled: Sequence[SubscriptionEventDocument],
    accepted: Sequence[SubscriptionEventDocument],
) -> list[ChurnReasonRow]:
    """Every reason given or saved in the period, most cancellations first."""

    cancellations: Counter[CancellationReason | None] = Counter(
        step.cancellation_reason for step in cancelled
    )
    saved: Counter[CancellationReason | None] = Counter(
        step.cancellation_reason for step in accepted
    )
    reasons: list[CancellationReason | None] = [
        *[
            reason
            for reason in CancellationReason
            if reason in cancellations or reason in saved
        ],
        *([None] if None in cancellations else []),
    ]
    rows = [
        ChurnReasonRow(
            reason=reason,
            cancellations=CancellationCount(cancellations[reason]),
            saved=SubscriptionStepCount(saved[reason]),
        )
        for reason in reasons
    ]
    return sorted(rows, key=lambda row: (-int(row.cancellations), -int(row.saved)))


def offer_rows(
    accepted: Sequence[SubscriptionEventDocument],
) -> list[RetentionOfferRow]:
    taken: Counter[RetentionOfferKind] = Counter(
        step.offer_kind for step in accepted if step.offer_kind is not None
    )
    return [
        RetentionOfferRow(kind=kind, accepted=SubscriptionStepCount(taken[kind]))
        for kind in RetentionOfferKind
        if taken[kind] > 0
    ]


def count_returns(
    win_backs: Sequence[SubscriptionEventDocument],
    billing: Sequence[ProductEventDocument],
) -> int:
    """Businesses that opened a subscription again after a win-back message."""

    first_win_back: dict[BusinessId, int] = {}
    for step in win_backs:
        moment: int = int(step.occurred_at)
        first_win_back[step.business_id] = min(
            first_win_back.get(step.business_id, moment), moment
        )

    returned: set[BusinessId] = {
        event.business_id
        for event in billing
        if event.name in RETURN_EVENTS
        and event.business_id is not None
        and event.business_id in first_win_back
        and int(event.occurred_at) > first_win_back[event.business_id]
    }
    return len(returned)


def comments(cancelled: Sequence[SubscriptionEventDocument]) -> list[ChurnComment]:
    """The owners' own words, newest first."""

    worded = [step for step in cancelled if step.details is not None]
    newest = sorted(worded, key=lambda step: int(step.occurred_at), reverse=True)
    return [
        ChurnComment(
            business_id=step.business_id,
            reason=step.cancellation_reason,
            details=step.details,
            occurred_at=step.occurred_at,
        )
        for step in newest[:MAX_COMMENTS]
        if step.details is not None
    ]
