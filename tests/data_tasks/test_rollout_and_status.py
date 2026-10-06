"""The release overlap from worker pulses, and how far the tasks are."""

from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import (
    DataTaskKind,
    DataTaskStatus,
    IndexedList,
)
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.dto.data_tasks import DataTaskDefinition
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.maintenance.data_task_progress import new_state
from app.utilities.maintenance.data_task_status import (
    effective_status,
    is_list_indexing,
    is_stalled,
    states_by_key,
    summarize_data_tasks,
)
from app.utilities.maintenance.rollout_overlap import (
    ROLLOUT_SETTLE_SECONDS,
    read_rollout,
)
from tests.data_tasks.data_task_support import (
    HOUR,
    MINUTE,
    NOW,
    OLD_RELEASE,
    RELEASE,
    SECOND,
    backfill_of,
    pulse,
    registry_of,
)

AT: Microseconds = Microseconds(NOW)
CONTACTS_V4 = DataTaskDefinition(
    key=DataTaskKey("migrate_documents:contacts"),
    kind=DataTaskKind.MIGRATE_DOCUMENTS,
    collection_name=DocumentCollectionName("contacts"),
    target_version=DocumentSchemaVersionNumber(4),
    lists=[IndexedList.CUSTOMERS],
)


def with_status(
    state: DataTaskStateDocument, status: DataTaskStatus
) -> DataTaskStateDocument:
    return state.model_copy(update={"status": status})


def test_the_overlap_is_over_when_only_this_release_beats() -> None:
    rollout = read_rollout([pulse(RELEASE, NOW - MINUTE)], RELEASE, AT)

    assert rollout.is_settled
    assert rollout.other_releases == []
    assert rollout.settles_at is None


def test_a_recent_pulse_of_the_previous_release_keeps_the_overlap_open() -> None:
    old_beat: int = NOW - 10 * MINUTE
    rollout = read_rollout(
        [pulse(RELEASE, NOW - MINUTE), pulse(OLD_RELEASE, old_beat, "worker-2")],
        RELEASE,
        AT,
    )

    assert not rollout.is_settled
    assert rollout.other_releases == [OLD_RELEASE]
    assert rollout.settles_at == old_beat + ROLLOUT_SETTLE_SECONDS * SECOND


def test_an_old_pulse_outside_the_settling_window_no_longer_counts() -> None:
    old_beat: int = NOW - ROLLOUT_SETTLE_SECONDS * SECOND - SECOND

    assert read_rollout([pulse(OLD_RELEASE, old_beat)], RELEASE, AT).is_settled


def test_an_unnamed_release_differs_from_a_named_one() -> None:
    assert not read_rollout([pulse(None, NOW - MINUTE)], RELEASE, AT).is_settled
    assert read_rollout([pulse(None, NOW - MINUTE)], None, AT).is_settled
    assert read_rollout([pulse(RELEASE, NOW)], None, AT).other_releases == [RELEASE]


def test_a_task_without_a_state_of_its_target_is_pending() -> None:
    older = new_state(CONTACTS_V4, AT).model_copy(
        update={
            "target_version": DocumentSchemaVersionNumber(3),
            "status": DataTaskStatus.DONE,
        }
    )
    done = with_status(new_state(CONTACTS_V4, AT), DataTaskStatus.DONE)

    assert effective_status(CONTACTS_V4, None) is DataTaskStatus.PENDING
    assert effective_status(CONTACTS_V4, older) is DataTaskStatus.PENDING
    assert effective_status(CONTACTS_V4, done) is DataTaskStatus.DONE


def test_a_task_stalls_a_day_after_it_became_due_unless_done() -> None:
    state = new_state(CONTACTS_V4, Microseconds(NOW - 24 * HOUR - SECOND))
    on_time = new_state(CONTACTS_V4, Microseconds(NOW - 24 * HOUR))

    assert is_stalled(CONTACTS_V4, state, AT)
    assert not is_stalled(CONTACTS_V4, on_time, AT)
    assert not is_stalled(CONTACTS_V4, with_status(state, DataTaskStatus.DONE), AT)
    assert not is_stalled(CONTACTS_V4, None, AT)


def test_the_summary_counts_open_failed_and_stalled_tasks_and_their_lists() -> None:
    registry = registry_of(
        backfills=[
            backfill_of("contacts", "last_seen_at", IndexedList.CUSTOMERS),
            backfill_of("knowledge_items", "updated_at", IndexedList.KNOWLEDGE),
            backfill_of("bookings", "source_channel"),
        ]
    )
    seen, knowledge, sources = registry.list_tasks()
    states = [
        with_status(
            new_state(seen, Microseconds(NOW - 30 * HOUR)), DataTaskStatus.FAILED
        ),
        with_status(new_state(knowledge, AT), DataTaskStatus.DONE),
    ]

    summary = summarize_data_tasks(registry.list_tasks(), states_by_key(states), AT)

    assert (summary.open_count, summary.failed_count, summary.stalled_count) == (
        2,
        1,
        1,
    )
    assert sources_is_open(sources, states)
    assert is_list_indexing([seen], states)
    assert not is_list_indexing([knowledge], states)
    assert not is_list_indexing([], states)


def sources_is_open(
    task: DataTaskDefinition, states: list[DataTaskStateDocument]
) -> bool:
    return effective_status(task, states_by_key(states).get(task.key)) is (
        DataTaskStatus.PENDING
    )
