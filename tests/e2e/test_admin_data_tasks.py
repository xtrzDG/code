"""
The post-deploy data tasks on the real application: the batch worker runs
them by itself, the platform admin sees and retries them, and the lists say
they are still indexing until the tasks that fill them are done.
"""

from collections.abc import Iterator
from typing import Any

import pytest

from app.schemas.constants.maintenance import DataTaskStatus
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import sign_in_and_create_restaurant

type JsonObject = dict[str, Any]

TASKS_URL: str = "/v1/admin/system/data-tasks"
SEEN: str = "backfill_lookup:contacts.last_seen_at"


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    running = start_workshop()
    with running.client:
        yield running


def fail(workshop: Workshop, key: str) -> None:
    repo = workshop.container.repositories.data_task_state_repo()
    with workshop.container.utilities.storage_scope().platform_wide():
        repo.modify(
            DataTaskKey(key),
            lambda state: state.model_copy(update={"status": DataTaskStatus.FAILED}),
        )


def test_the_worker_runs_the_tasks_and_the_lists_stop_indexing(
    workshop: Workshop,
) -> None:
    owner_token, _, business_id = sign_in_and_create_restaurant(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    customers = f"/v1/businesses/{business_id}/contacts"
    knowledge = f"/v1/businesses/{business_id}/knowledge"

    before = workshop.client.get(TASKS_URL, headers=bearer(admin_token)).json()
    indexing = workshop.client.get(customers, headers=bearer(owner_token)).json()
    workshop.container.gateways.background_worker().run_once()
    after = workshop.client.get(TASKS_URL, headers=bearer(admin_token)).json()
    complete = workshop.client.get(customers, headers=bearer(owner_token)).json()
    articles = workshop.client.get(knowledge, headers=bearer(owner_token)).json()

    assert before["open_count"] == len(before["tasks"]) > 0
    assert {task["status"] for task in before["tasks"]} == {"pending"}
    assert before["batch_size"] == 5000 and before["rollout"]["is_settled"] is True
    assert indexing["is_indexing"] is True
    assert after["open_count"] == 0 and after["failed_count"] == 0
    assert {task["status"] for task in after["tasks"]} == {"done"}
    assert complete["is_indexing"] is False and articles["is_indexing"] is False


def test_the_admin_retries_a_failed_task_and_nobody_else_can(
    workshop: Workshop,
) -> None:
    owner_token, _, _ = sign_in_and_create_restaurant(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    workshop.container.gateways.background_worker().run_once()
    fail(workshop, SEEN)
    retry_url = f"{TASKS_URL}/{SEEN}/retry"

    refused = workshop.client.post(retry_url, headers=bearer(owner_token))
    anonymous = workshop.client.get(TASKS_URL)
    listed = workshop.client.get(TASKS_URL, headers=bearer(admin_token)).json()
    retried = workshop.client.post(retry_url, headers=bearer(admin_token))
    again = workshop.client.post(retry_url, headers=bearer(admin_token))
    unknown = workshop.client.post(
        f"{TASKS_URL}/backfill_lookup:contacts.nickname/retry",
        headers=bearer(admin_token),
    )
    malformed = workshop.client.post(
        f"{TASKS_URL}/drop%20table/retry", headers=bearer(admin_token)
    )

    assert refused.status_code == 403
    assert anonymous.status_code == 401
    assert listed["failed_count"] == 1 and listed["tasks"][0]["key"] == SEEN
    assert retried.status_code == 200, retried.text
    body: JsonObject = retried.json()
    assert body["task"]["status"] == "pending" and body["audit_log_entry_id"]
    assert again.status_code == 409
    assert unknown.status_code == 404
    assert malformed.status_code in {404, 422}
