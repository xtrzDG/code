"""The steps of a subscription's life as the use cases record them."""

from typed_time_provider import Microseconds

from app.schemas.constants.billing import SubscriptionStatus
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.domain.billing import SubscriptionDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.typings.users.prefixed_id import UserId


def lifecycle_event(
    subscription: SubscriptionDocument,
    kind: SubscriptionEventKind,
    now: Microseconds,
    actor_id: UserId | None = None,
) -> SubscriptionEventDocument:
    """A step of the subscription happening now, with its pause if it has one."""

    return SubscriptionEventDocument(
        business_id=subscription.business_id,
        subscription_id=subscription.id,
        kind=kind,
        occurred_at=now,
        actor_id=actor_id,
        pause_starts_at=subscription.pause_starts_at,
        pause_until=subscription.pause_until,
        created_at=now,
        updated_at=now,
    )


def pause_ended_event(
    subscription: SubscriptionDocument,
    now: Microseconds,
    actor_id: UserId | None = None,
) -> SubscriptionEventDocument | None:
    """
    The RESUMED step of the subscription's pause, which ends now: a pause
    not started yet is called off (it ends at its start and counts no
    month); None without a pause.
    """

    starts_at: Microseconds | None = subscription.pause_starts_at
    if starts_at is None or subscription.pause_until is None:
        return None

    ends_at: Microseconds = (
        now if subscription.status is SubscriptionStatus.PAUSED else starts_at
    )
    event: SubscriptionEventDocument = lifecycle_event(
        subscription, SubscriptionEventKind.RESUMED, now, actor_id
    )
    return event.model_copy(
        update={"pause_until": min(ends_at, subscription.pause_until, key=int)}
    )


def clear_pause(subscription: SubscriptionDocument) -> None:
    """The subscription has no pause any more."""

    subscription.pause_starts_at = None
    subscription.pause_until = None
