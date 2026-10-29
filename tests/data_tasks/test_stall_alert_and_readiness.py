"""BACKFILL_STALLED, the data-task line of /readyz and the lists' hint."""

from typed_time_provider import Microseconds

from app.schemas.constants.maintenance import DataTaskStatus, IndexedList
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.constants.observability import HealthCheckStatus
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.use_cases.admin.alerts.alert_rules import PLATFORM_ALERT_RULES
from app.use_cases.observability.data_task_readiness import check_data_tasks
from app.use_cases.shared.list_indexing import read_list_indexing
from app.utilities.maintenance.data_task_progress import new_state
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.data_tasks.data_task_support import (
    HOUR,
    backfill_of,
    data_task_states,
    registry_of,
)
from tests.platform_ops.ops_documents import NOW
from tests.platform_ops.ops_world import OpsWorld

BACKFILLS = [
    backfill_of("contacts", "last_seen_at", IndexedList.CUSTOMERS),
    backfill_of("contacts", "display_name_folded", IndexedList.CUSTOMERS),
    backfill_of("knowledge_items", "updated_at", IndexedList.KNOWLEDGE),
    backfill_of("bookings", "source_channel"),
    backfill_of("leads", "source_channel"),
]


def stalled_world(stalled: int) -> OpsWorld:
    world = OpsWorld()
    world.data_task_registry = registry_of(backfills=BACKFILLS)
    for task in world.data_task_registry.list_tasks()[:stalled]:
        world.data_task_states.save(new_state(task, Microseconds(int(NOW) - 25 * HOUR)))
    return world


def test_backfill_stalled_fires_for_a_task_not_done_a_day_after_it_was_due() -> None:
    rule = {
        PlatformAlertCode.BACKFILL_STALLED: PLATFORM_ALERT_RULES[
            PlatformAlertCode.BACKFILL_STALLED
        ]
    }

    quiet = stalled_world(0).checks().run(rule, NOW)[0]
    one = stalled_world(1).checks().run(rule, NOW)[0]
    many = stalled_world(5).checks().run(rule, NOW)[0]

    assert (quiet.is_firing, int(quiet.figure)) == (False, 0)
    assert (one.is_firing, int(one.figure)) == (True, 1)
    assert "backfill_lookup:contacts.last_seen_at" in str(one.detail)
    assert (many.is_firing, int(many.figure)) == (True, 5)
    assert str(many.detail).endswith("and 2 more. See the system page.")


def test_a_done_task_never_stalls() -> None:
    world = stalled_world(1)
    [state] = world.data_task_states.get_many(
        [DataTaskKey("backfill_lookup:contacts.last_seen_at")]
    )
    world.data_task_states.save(
        state.model_copy(update={"status": DataTaskStatus.DONE})
    )
    rule = {
        PlatformAlertCode.BACKFILL_STALLED: PLATFORM_ALERT_RULES[
            PlatformAlertCode.BACKFILL_STALLED
        ]
    }

    assert world.checks().run(rule, NOW)[0].is_firing is False


def test_readiness_reports_open_tasks_without_stopping_traffic() -> None:
    registry = registry_of(backfills=BACKFILLS[:2])
    states = data_task_states()
    first, second = registry.list_tasks()
    states.save(
        new_state(first, Microseconds(int(NOW) - 30 * HOUR)).model_copy(
            update={
                "status": DataTaskStatus.FAILED,
                "failed_document_keys": [StoredDocumentKey("doc_1")],
            }
        )
    )

    check = check_data_tasks(registry, states, StorageScopeContext(), NOW)
    states.save(
        new_state(first, NOW).model_copy(update={"status": DataTaskStatus.DONE})
    )
    states.save(
        new_state(second, NOW).model_copy(update={"status": DataTaskStatus.DONE})
    )
    done = check_data_tasks(registry, states, StorageScopeContext(), NOW)

    assert check.status is HealthCheckStatus.DEGRADED
    assert (int(check.open or 0), int(check.failed or 0), int(check.stalled or 0)) == (
        2,
        1,
        1,
    )
    assert done.status is HealthCheckStatus.OK
    assert int(done.open or 0) == 0


def test_a_list_is_indexing_while_a_task_that_fills_it_is_open() -> None:
    registry = registry_of(backfills=BACKFILLS)
    states = data_task_states()
    for task in registry.tasks_for_list(IndexedList.KNOWLEDGE):
        states.save(
            new_state(task, NOW).model_copy(update={"status": DataTaskStatus.DONE})
        )

    assert read_list_indexing(registry, states, IndexedList.CUSTOMERS) is True
    assert read_list_indexing(registry, states, IndexedList.KNOWLEDGE) is False
