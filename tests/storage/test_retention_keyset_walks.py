"""
The retention purge's keyset walks on both storages: every record of a
window exactly once, in order, across batches, even with equal timestamps
(conversations by their last message, leads by creation, bookings by the
visit's end in seconds).
"""

import pytest
from typed_time_provider import Microseconds

from app.schemas.dto.retention import RetentionWindow
from app.schemas.typings.privacy.constrained_integers import RetentionBatchSize
from app.use_cases.compliance.retention.retention_walk import walk_batches
from tests.storage.conftest import CollectionFactory
from tests.storage.retention_world import DAY_MICROSECONDS, RetentionWorld

pytestmark = pytest.mark.usefixtures("platform_scope")
SMALL_BATCH: RetentionBatchSize = RetentionBatchSize(2)


def test_walks_return_each_record_of_the_window_once_across_batches(
    collections: CollectionFactory,
) -> None:
    world = RetentionWorld(collections)
    business = world.new_business()
    # Two pairs share a moment; one history is newer than the window.
    histories = [
        world.history(business, days_ago=days) for days in (900, 900, 850, 820, 820)
    ]
    world.history(business, days_ago=10)
    window = RetentionWindow(
        since=Microseconds(world.clock.now - 1000 * DAY_MICROSECONDS),
        before=world.clock.days_ago(800),
    )
    conversations = world.quiet_conversations
    leads = world.expiring_leads
    bookings = world.expiring_bookings

    walked_conversations = list(
        walk_batches(
            lambda after: conversations.page_quiet_in(
                business.id, window, after, SMALL_BATCH
            ),
            SMALL_BATCH,
        )
    )
    walked_leads = list(
        walk_batches(
            lambda after: leads.page_in(business.id, window, after, SMALL_BATCH),
            SMALL_BATCH,
        )
    )
    walked_bookings = list(
        walk_batches(
            lambda after: bookings.page_in(business.id, window, after, SMALL_BATCH),
            SMALL_BATCH,
        )
    )

    assert [item.id for item in walked_conversations] == [
        history.conversation.id for history in histories
    ]
    assert [item.id for item in walked_leads] == [
        history.lead.id for history in histories
    ]
    assert [item.id for item in walked_bookings] == [
        history.booking.id for history in histories
    ]
