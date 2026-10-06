"""The admin Metrics page's churn: reasons, saves, pauses and win-backs."""

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.subscription_lifecycle import (
    CancellationReason,
    RetentionOfferKind,
    SubscriptionEventKind,
    WinBackStage,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.typings.analytics.constrained_strings import MetricsDate
from app.schemas.typings.billing.prefixed_id import SubscriptionId
from app.schemas.typings.subscription_lifecycle.constrained_strings import (
    CancellationDetails,
)
from tests.analytics.metric_events import at_day, billing
from tests.analytics.metrics_world import MetricsWorld


def step(
    world: MetricsWorld,
    business: BusinessDocument,
    kind: SubscriptionEventKind,
    day: float,
    **fields: object,
) -> None:
    moment = at_day(day)
    event = SubscriptionEventDocument(
        business_id=business.id,
        subscription_id=SubscriptionId(),
        kind=kind,
        occurred_at=moment,
        created_at=moment,
        updated_at=moment,
    )
    world.lifecycle_steps.record(event.model_copy(update=fields))


def churn_world() -> tuple[MetricsWorld, BusinessDocument, BusinessDocument]:
    world = MetricsWorld()
    first = world.add_business(world.add_user(1), 1)
    second = world.add_business(world.add_user(2), 2)
    seasonal = CancellationReason.SEASONAL_BREAK
    step(
        world,
        first,
        SubscriptionEventKind.CANCELLED,
        20,
        cancellation_reason=seasonal,
        details=CancellationDetails("Closed until May"),
    )
    step(
        world,
        second,
        SubscriptionEventKind.CANCELLED,
        25,
        cancellation_reason=CancellationReason.TOO_EXPENSIVE,
    )
    step(world, second, SubscriptionEventKind.CANCELLED, 26)
    step(
        world,
        first,
        SubscriptionEventKind.OFFER_ACCEPTED,
        22,
        cancellation_reason=seasonal,
        offer_kind=RetentionOfferKind.PAUSE,
    )
    step(world, first, SubscriptionEventKind.PAUSE_SCHEDULED, 22)
    step(world, first, SubscriptionEventKind.RESUMED, 40)
    step(
        world,
        second,
        SubscriptionEventKind.WIN_BACK_SENT,
        39,
        win_back_stage=WinBackStage.DAY_14,
    )
    # Before the period: not counted.
    step(
        world,
        first,
        SubscriptionEventKind.CANCELLED,
        2,
        cancellation_reason=CancellationReason.OTHER,
    )
    world.record(billing(ProductEventName.SUBSCRIBED, 41, second.id, amount=29300))
    return world, first, second


def test_cancellations_count_by_reason_with_the_saves_of_each() -> None:
    world, _, _ = churn_world()

    churn = world.metrics(period_start=MetricsDate("2026-09-15")).churn

    assert churn.cancellations == 3
    rows = {row.reason: (row.cancellations, row.saved) for row in churn.reasons}
    assert rows == {
        CancellationReason.SEASONAL_BREAK: (1, 1),
        CancellationReason.TOO_EXPENSIVE: (1, 0),
        None: (1, 0),
    }
    assert [(row.kind, row.accepted) for row in churn.offers] == [
        (RetentionOfferKind.PAUSE, 1)
    ]


def test_pauses_win_backs_and_returns_are_counted() -> None:
    world, _, _ = churn_world()

    churn = world.metrics(period_start=MetricsDate("2026-09-15")).churn

    assert churn.pauses_scheduled == 1
    assert churn.pauses_ended == 1
    assert churn.win_back_sent == 1
    # The second business subscribed again after its win-back message.
    assert churn.returned_after_win_back == 1


def test_the_owners_words_come_newest_first() -> None:
    world, first, _ = churn_world()

    [comment] = world.metrics(period_start=MetricsDate("2026-09-15")).churn.comments

    assert comment.business_id == first.id
    assert str(comment.details) == "Closed until May"
    assert comment.reason is CancellationReason.SEASONAL_BREAK


def test_the_filters_keep_churn_to_the_businesses_in_scope() -> None:
    world, _, _ = churn_world()

    churn = world.metrics(
        period_start=MetricsDate("2026-09-15"), country_code="IT"
    ).churn

    assert churn.cancellations == 0 and churn.reasons == []
