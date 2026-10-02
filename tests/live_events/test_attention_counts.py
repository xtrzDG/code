"""What waits for a person: the counts behind the navigation badges."""

import pytest

from app.schemas.dto.operations.attention_counts import AttentionCountsQuery
from app.schemas.dto.operations.inbox_counts import InboxCountsQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.live_events.attention_seeding import seed_waiting_items
from tests.live_events.live_api import (
    OTHER_OWNER_TOKEN,
    OWNER_TOKEN,
    STAFF_TOKEN,
    LiveApi,
)
from tests.operations.operations_world import OperationsWorld


def seeded_api() -> LiveApi:
    api = LiveApi()
    seed_waiting_items(api.world, api.business, api.other_business)
    return api


def test_each_count_holds_only_what_waits_for_a_person() -> None:
    api = seeded_api()

    counts = api.world.get_attention_counts().run(
        AttentionCountsQuery(business_id=api.business.id)
    )

    assert counts.business_id == api.business.id
    assert counts.open_handoff_count == 3
    assert counts.new_lead_count == 2
    assert counts.unconfirmed_booking_count == 1
    assert counts.channel_error_count == 1


def test_the_inbox_counts_are_two_of_the_attention_counts() -> None:
    api = seeded_api()

    inbox = api.world.inbox_counts().run(InboxCountsQuery(business_id=api.business.id))

    assert (inbox.open_handoff_count, inbox.new_lead_count) == (3, 2)


def test_members_read_the_counts_and_strangers_get_not_found() -> None:
    api = seeded_api()

    for token in (OWNER_TOKEN, STAFF_TOKEN):
        response = api.get("/attention-counts", token=token)
        assert response.status_code == 200
        assert response.json() == {
            "business_id": str(api.business.id),
            "open_handoff_count": 3,
            "new_lead_count": 2,
            "unconfirmed_booking_count": 1,
            "channel_error_count": 1,
        }

    assert api.get("/attention-counts", token=OTHER_OWNER_TOKEN).status_code == 404
    assert api.client.get(api.url("/attention-counts")).status_code == 401


def test_counts_of_a_missing_business_are_not_found() -> None:
    with pytest.raises(NotFoundError):
        OperationsWorld().get_attention_counts().run(
            AttentionCountsQuery(business_id=BusinessId())
        )
