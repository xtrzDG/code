"""What waits for a person: one count behind the inbox tabs and every badge."""

import pytest

from app.schemas.dto.inbox.inbox_attention import InboxAttentionQuery
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from tests.live_events.attention_seeding import seed_waiting_items
from tests.live_events.live_api import (
    OTHER_OWNER_TOKEN,
    OWNER_TOKEN,
    STAFF_TOKEN,
    LiveApi,
)

EXPECTED_COUNTS: dict[str, int] = {
    "needs_person": 3,
    "requests": 2,
    "unassigned": 5,
    "mine": 0,
    "unconfirmed_bookings": 1,
    "channel_errors": 1,
    # The names /attention-counts used before 2026-10, the same numbers.
    "open_handoff_count": 3,
    "new_lead_count": 2,
    "unconfirmed_booking_count": 1,
    "channel_error_count": 1,
}


def seeded_api() -> LiveApi:
    api = LiveApi()
    seed_waiting_items(api.world, api.business, api.other_business)
    return api


def test_each_count_holds_only_what_waits_for_a_person() -> None:
    api = seeded_api()

    counts = api.world.count_attention().run(
        InboxAttentionQuery(user_id=api.owner_id, business_id=api.business.id)
    )

    assert counts.business_id == api.business.id
    assert counts.model_dump(mode="json", exclude={"business_id"}) == EXPECTED_COUNTS


def test_members_read_the_counts_and_strangers_get_not_found() -> None:
    api = seeded_api()

    for token in (OWNER_TOKEN, STAFF_TOKEN):
        response = api.get("/attention-counts", token=token)
        assert response.status_code == 200
        assert response.json() == {"business_id": str(api.business.id)} | (
            EXPECTED_COUNTS
        )

    assert api.get("/attention-counts", token=OTHER_OWNER_TOKEN).status_code == 404
    assert api.client.get(api.url("/attention-counts")).status_code == 401


def test_reading_the_counts_records_no_view() -> None:
    api = seeded_api()
    audited_before = len(api.world.audit_repo.list_by_business(api.business.id))

    for token in (OWNER_TOKEN, STAFF_TOKEN):
        assert api.get("/attention-counts", token=token).status_code == 200

    assert len(api.world.audit_repo.list_by_business(api.business.id)) == (
        audited_before
    )


def test_counts_of_a_missing_business_are_not_found() -> None:
    api = seeded_api()

    with pytest.raises(NotFoundError):
        api.world.count_attention().run(
            InboxAttentionQuery(user_id=api.owner_id, business_id=BusinessId())
        )
