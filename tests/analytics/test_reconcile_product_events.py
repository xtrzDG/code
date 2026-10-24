"""
The daily reconciliation over the real container: steps recorded live are
not stored twice, and steps never recorded (data from before analytics)
are derived from the stored records; both daily jobs are scheduled.
"""

from collections import Counter
from typing import cast

from typed_time_provider import Microseconds

from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.growth_analytics import (
    GROWTH_ANALYTICS_INTERVAL,
    PURGE_WEB_VITALS_JOB,
    RECONCILE_PRODUCT_EVENTS_JOB,
)
from app.schemas.constants.analytics import ProductEventName, ProductEventSource
from app.schemas.dto.jobs import JobTick
from tests.analytics.test_launch_journey_events import stored_events
from tests.e2e.harness import Workshop
from tests.setup.launch_steps import (
    accept_dpa,
    add_staff_contact,
    create_assistant,
    fill_profile,
    go_live,
)

ONCE_ONLY: tuple[ProductEventName, ...] = (
    ProductEventName.SIGNED_UP,
    ProductEventName.BUSINESS_CREATED,
    ProductEventName.WENT_LIVE,
    ProductEventName.TRIAL_STARTED,
)


def reconcile(workshop: Workshop) -> int:
    operator = (
        workshop.container.operators.analytics.reconcile_product_events_operator()
    )
    report = operator.operate(
        JobTick(
            job_name=RECONCILE_PRODUCT_EVENTS_JOB,
            scheduled_at=workshop.clock.wall_clock.now_unix(),
        )
    )
    return int(report.processed_count)


def live_owner(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)
    accept_dpa(workshop, assistant)
    go_live(workshop, assistant)


def once_only_counts(workshop: Workshop) -> Counter[ProductEventName]:
    return Counter(
        event.name for event in stored_events(workshop) if event.name in ONCE_ONLY
    )


def test_steps_recorded_live_are_not_stored_twice(workshop: Workshop) -> None:
    live_owner(workshop)
    before = len(stored_events(workshop))

    assert reconcile(workshop) > 0
    assert len(stored_events(workshop)) == before
    assert once_only_counts(workshop) == dict.fromkeys(ONCE_ONLY, 1)


def test_missing_steps_are_derived_from_the_records(workshop: Workshop) -> None:
    live_owner(workshop)
    collection = workshop.container.analytics_collections.product_event_collection()
    for event in stored_events(workshop):
        collection.delete(str(event.id))

    reconcile(workshop)
    reconcile(workshop)

    events = stored_events(workshop)
    assert once_only_counts(workshop) == dict.fromkeys(ONCE_ONLY, 1)
    assert {event.source for event in events} == {ProductEventSource.RECONCILIATION}
    (created,) = [e for e in events if e.name is ProductEventName.BUSINESS_CREATED]
    assert created.user_id is not None
    trial = next(e for e in events if e.name is ProductEventName.TRIAL_STARTED)
    assert trial.properties.trial_ends_at is not None
    assert int(trial.properties.trial_ends_at) > int(trial.occurred_at)
    # A trial is not a payment: nothing to correct in billing.
    assert not [e for e in events if e.name is ProductEventName.SUBSCRIBED]


def test_both_daily_jobs_are_scheduled(workshop: Workshop) -> None:
    specs = cast(list[PeriodicJobSpec], workshop.container.gateways.periodic_jobs())
    daily = {
        spec.name: spec.interval_seconds
        for spec in specs
        if spec.name in {PURGE_WEB_VITALS_JOB, RECONCILE_PRODUCT_EVENTS_JOB}
    }

    assert daily == {
        PURGE_WEB_VITALS_JOB: GROWTH_ANALYTICS_INTERVAL,
        RECONCILE_PRODUCT_EVENTS_JOB: GROWTH_ANALYTICS_INTERVAL,
    }
    purge = workshop.container.operators.analytics.purge_web_vitals_operator()
    report = purge.operate(
        JobTick(job_name=PURGE_WEB_VITALS_JOB, scheduled_at=Microseconds(0))
    )
    assert int(report.processed_count) == 0
