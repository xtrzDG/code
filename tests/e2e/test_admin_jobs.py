"""The dead-letter API of the real application: list, retry and discard jobs."""

from typing import cast

from app.containers.app import AppContainer
from app.contracts.jobs import QueuedJobOperator
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.workshop_container import replace_provider
from tests.platform.worker_fakes import FlakyQueuedOperator

SEND_DIGEST: JobName = JobName("send_owner_digest")
SECRET_PAYLOAD: JobPayloadJson = JobPayloadJson('{"customer": "+995599123456"}')


def start_with_flaky_job(failures: int) -> tuple[Workshop, FlakyQueuedOperator]:
    operator = FlakyQueuedOperator(failures_before_success=failures)

    def register(container: AppContainer) -> None:
        handlers = cast(
            dict[JobName, QueuedJobOperator],
            container.gateways.queued_job_operators(),
        )
        replace_provider(
            container.gateways.queued_job_operators,
            {**handlers, SEND_DIGEST: operator},
        )

    return start_workshop(prepare=register), operator


def test_a_dead_job_is_retried_through_the_api() -> None:
    workshop, operator = start_with_flaky_job(failures=5)
    business_id = BusinessId()
    job_id = workshop.container.facilitators.job_queue_facilitator().enqueue(
        SEND_DIGEST, SECRET_PAYLOAD, business_id
    )
    worker = workshop.container.gateways.background_worker()
    for _ in range(5):
        worker.run_once()
        workshop.clock.advance(10_000)
    # Signed in now: an admin session unused for twelve hours ends.
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)

    dead = workshop.client.get(
        "/v1/admin/jobs",
        params={"status": "dead", "name": str(SEND_DIGEST)},
        headers=bearer(admin_token),
    )
    retried = workshop.client.post(
        f"/v1/admin/jobs/{job_id}/retry", headers=bearer(admin_token)
    )
    retried_again = workshop.client.post(
        f"/v1/admin/jobs/{job_id}/retry", headers=bearer(admin_token)
    )
    report = worker.run_once()
    done = workshop.client.get(
        "/v1/admin/jobs", params={"status": "done"}, headers=bearer(admin_token)
    )

    assert dead.status_code == 200, dead.text
    [dead_job] = dead.json()["items"]
    assert dead_job["id"] == str(job_id)
    assert dead_job["status"] == "dead"
    assert dead_job["attempts"] == 5
    assert dead_job["lane"] == "default"
    assert dead_job["business_id"] == str(business_id)
    assert dead_job["last_error"] == "ExternalServiceError: provider down"
    assert "payload" not in dead_job and "+995" not in dead.text
    assert dead.json()["next_cursor"] is None

    assert retried.status_code == 200, retried.text
    assert retried.json()["job"]["status"] == "pending"
    assert retried.json()["job"]["attempts"] == 0
    assert retried_again.status_code == 409
    assert report.queued_runs == 1
    assert [item["id"] for item in done.json()["items"]] == [str(job_id)]
    assert len(operator.calls) == 6
    assert [entry.action for entry in audit_entries(workshop, business_id)] == [
        AuditAction.UPDATE
    ]


def test_jobs_are_discarded_and_only_admins_may_touch_the_queue() -> None:
    workshop, _ = start_with_flaky_job(failures=0)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    owner_token, _ = workshop.sign_in_with_email("owner@cafe.example")
    queue = workshop.container.facilitators.job_queue_facilitator()
    waiting_id = queue.enqueue(
        SEND_DIGEST, SECRET_PAYLOAD, None, run_at=workshop.clock.wall_clock.now_unix()
    )
    done_id = queue.enqueue(SEND_DIGEST, SECRET_PAYLOAD, None)
    workshop.container.repositories.queued_job_repo().update(
        done_id, lambda job: setattr(job, "status", QueuedJobStatus.DONE)
    )

    discarded = workshop.client.post(
        f"/v1/admin/jobs/{waiting_id}/discard", headers=bearer(admin_token)
    )
    report = workshop.container.gateways.background_worker().run_once()
    refused = workshop.client.post(
        f"/v1/admin/jobs/{done_id}/discard", headers=bearer(admin_token)
    )
    revived = workshop.client.post(
        f"/v1/admin/jobs/{waiting_id}/retry", headers=bearer(admin_token)
    )
    paged = workshop.client.get(
        "/v1/admin/jobs", params={"limit": "1"}, headers=bearer(admin_token)
    )
    next_page = workshop.client.get(
        "/v1/admin/jobs",
        params={"limit": "1", "cursor": paged.json()["next_cursor"]},
        headers=bearer(admin_token),
    )

    assert discarded.status_code == 200, discarded.text
    assert discarded.json()["job"]["status"] == "discarded"
    assert report.queued_runs == 0  # a discarded job never runs
    assert refused.status_code == 409
    assert revived.status_code == 200
    assert paged.status_code == 200 and len(paged.json()["items"]) == 1
    assert next_page.status_code == 200 and len(next_page.json()["items"]) == 1
    assert {
        item["id"] for item in paged.json()["items"] + next_page.json()["items"]
    } == {
        str(waiting_id),
        str(done_id),
    }
    assert [entry.action for entry in audit_entries(workshop, None)] == [
        AuditAction.DELETE,
        AuditAction.UPDATE,
    ]

    retry_path = f"/v1/admin/jobs/{waiting_id}/retry"
    client = workshop.client
    assert client.get("/v1/admin/jobs").status_code == 401
    assert client.get("/v1/admin/jobs", headers=bearer(owner_token)).status_code == 403
    assert client.post(retry_path, headers=bearer(owner_token)).status_code == 403
    assert (
        client.post(
            "/v1/admin/jobs/queued_job_nope/retry", headers=bearer(admin_token)
        ).status_code
        == 404
    )
    for params in ({"status": "sleeping"}, {"name": "Not A Name"}, {"limit": "0"}):
        response = workshop.client.get(
            "/v1/admin/jobs", params=params, headers=bearer(admin_token)
        )
        assert response.status_code == 422, params


def audit_entries(
    workshop: Workshop,
    business_id: BusinessId | None,
) -> list[AuditLogEntryDocument]:
    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    return [
        entry
        for entry in entries.list_all()
        if entry.business_id == business_id and str(entry.entity) == "queued_job"
    ]
