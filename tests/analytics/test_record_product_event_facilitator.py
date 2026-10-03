"""The facilitator gives steps their ids and times and never fails the action."""

import logging
from collections.abc import Sequence

import pytest
from typed_time_provider import Microseconds

from app.contracts.repositories.analytics_repositories import (
    ProductEventRepoContract,
)
from app.facilitators.product_events.record_product_event_facilitator import (
    RecordProductEventFacilitator,
)
from app.schemas.constants.analytics import ProductEventName, ProductEventSource
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.product_events import (
    ProductEventDocument,
    ProductEventProperties,
)
from app.schemas.dto.analytics.product_event_drafts import ProductEventDraft
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.users.prefixed_id import UserId
from tests.analytics.analytics_fakes import SettableClock, product_event_repo

FAR_FUTURE: Microseconds = Microseconds(10**17)


class BrokenRepository(ProductEventRepoContract):
    def record(self, event: ProductEventDocument) -> IsDocumentInserted:
        raise RuntimeError("storage is down")

    def list_named(
        self,
        names: Sequence[ProductEventName],
        occurred_from: Microseconds | None,
        occurred_before: Microseconds,
    ) -> list[ProductEventDocument]:
        return []


def test_a_once_only_step_is_stored_once_and_a_repeatable_one_each_time() -> None:
    clock = SettableClock()
    repo = product_event_repo()
    facilitator = RecordProductEventFacilitator(repo, clock.wall_clock())
    user_id = UserId()
    business_id = BusinessId()

    for _ in range(2):
        facilitator.record(
            ProductEventDraft(name=ProductEventName.SIGNED_UP, user_id=user_id),
            ProductEventDraft(name=ProductEventName.SIGNED_IN, user_id=user_id),
            ProductEventDraft(name=ProductEventName.WENT_LIVE, business_id=business_id),
        )

    names = [
        event.name
        for event in repo.list_named(list(ProductEventName), None, FAR_FUTURE)
    ]
    assert names.count(ProductEventName.SIGNED_UP) == 1
    assert names.count(ProductEventName.WENT_LIVE) == 1
    assert names.count(ProductEventName.SIGNED_IN) == 2


def test_each_channel_kind_counts_its_first_connection() -> None:
    clock = SettableClock()
    repo = product_event_repo()
    facilitator = RecordProductEventFacilitator(repo, clock.wall_clock())
    business_id = BusinessId()

    for channel in (ChannelKind.TELEGRAM, ChannelKind.TELEGRAM, ChannelKind.WEB_CHAT):
        facilitator.record(
            ProductEventDraft(
                name=ProductEventName.CHANNEL_CONNECTED,
                business_id=business_id,
                properties=ProductEventProperties(channel=channel),
            )
        )

    stored = repo.list_named([ProductEventName.CHANNEL_CONNECTED], None, FAR_FUTURE)
    assert sorted(str(event.properties.channel) for event in stored) == [
        "telegram",
        "web_chat",
    ]


def test_a_step_keeps_when_it_happened_and_when_it_was_written() -> None:
    clock = SettableClock()
    repo = product_event_repo()
    facilitator = RecordProductEventFacilitator(repo, clock.wall_clock())
    earlier = Microseconds(clock.microseconds - 3_600_000_000)

    facilitator.record(
        ProductEventDraft(
            name=ProductEventName.FIRST_BOOKING,
            business_id=BusinessId(),
            occurred_at=earlier,
        ),
        ProductEventDraft(name=ProductEventName.SIGNED_IN, user_id=UserId()),
    )

    booking, sign_in = repo.list_named(list(ProductEventName), None, FAR_FUTURE)
    assert booking.occurred_at == earlier
    assert booking.created_at == clock.now()
    assert sign_in.occurred_at == clock.now()
    assert booking.source is ProductEventSource.SERVER


def test_a_failed_write_is_logged_and_never_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    facilitator = RecordProductEventFacilitator(
        BrokenRepository(), SettableClock().wall_clock()
    )

    with caplog.at_level(logging.WARNING):
        facilitator.record(
            ProductEventDraft(name=ProductEventName.SIGNED_IN, user_id=UserId())
        )

    assert "signed_in was not recorded" in caplog.text


def test_reading_by_name_respects_the_time_range() -> None:
    clock = SettableClock()
    repo = product_event_repo()
    facilitator = RecordProductEventFacilitator(repo, clock.wall_clock())
    facilitator.record(
        ProductEventDraft(name=ProductEventName.SIGNED_IN, user_id=UserId())
    )
    clock.microseconds += 1_000
    facilitator.record(
        ProductEventDraft(name=ProductEventName.SIGNED_IN, user_id=UserId())
    )

    later = repo.list_named(
        [ProductEventName.SIGNED_IN], Microseconds(clock.microseconds), FAR_FUTURE
    )
    earlier = repo.list_named(
        [ProductEventName.SIGNED_IN], None, Microseconds(clock.microseconds)
    )

    assert len(later) == 1
    assert len(earlier) == 1
