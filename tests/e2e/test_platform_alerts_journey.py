"""
The platform alerts on the real worker: a dead job pages the team's
Telegram chat through the platform bot once, again only after the
cooldown, and once more when the dead letter is gone; the system page
shows the episode. The worker ticks every few minutes throughout, as a
live one does, so its periodic jobs' heartbeats stay fresh and the
missed-run alert stays quiet.
"""

from collections.abc import Iterator
from typing import cast

import pytest

from app.containers.app import AppContainer
from app.contracts.jobs import QueuedJobOperator
from app.gateways.worker.background_worker import BackgroundWorker
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL, E2E_ENVIRONMENT
from tests.e2e.workshop_container import replace_provider
from tests.platform.worker_fakes import FlakyQueuedOperator

ALERT_CHAT: str = "-1001234567890"
DOOMED_JOB: JobName = JobName("send_owner_digest")
MINUTE_SECONDS: int = 60
# Longer than the queue's last retry backoff (30 s x 2^3), shorter than the
# missed-run grace of the most frequent periodic jobs (interval + 30 min).
TICK_MINUTES: int = 5
ALERTING_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "PLATFORM_ALERT_TELEGRAM_CHAT_IDS": ALERT_CHAT,
    "PLATFORM_ALERT_COOLDOWN_MINUTES": "60",
    "CABINET_BASE_URL": "https://cabinet.workshop.example",
}


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    def register(container: AppContainer) -> None:
        handlers = cast(
            dict[JobName, QueuedJobOperator],
            container.gateways.queued_job_operators(),
        )
        replace_provider(
            container.gateways.queued_job_operators,
            {**handlers, DOOMED_JOB: FlakyQueuedOperator(failures_before_success=99)},
        )

    running = start_workshop(ALERTING_ENVIRONMENT, prepare=register)
    with running.client:
        yield running


def alert_texts(workshop: Workshop) -> list[str]:
    return [
        str(body["text"])
        for body in workshop.telegram.bodies("/sendMessage")
        if str(body["chat_id"]) == ALERT_CHAT
    ]


def tick_after(workshop: Workshop, worker: BackgroundWorker, minutes: int) -> None:
    workshop.clock.advance(minutes * MINUTE_SECONDS)
    # The alert job queues its messages; the queue pass sends them.
    worker.run_once()


def wait(workshop: Workshop, worker: BackgroundWorker, minutes: int) -> None:
    for _ in range(minutes // TICK_MINUTES):
        tick_after(workshop, worker, TICK_MINUTES)


def kill_one_job(workshop: Workshop, worker: BackgroundWorker) -> str:
    job_id = workshop.container.facilitators.job_queue_facilitator().enqueue(
        DOOMED_JOB, JobPayloadJson("{}"), None
    )
    worker.run_once()
    # Five attempts, each retry due within one tick.
    for _ in range(4):
        workshop.clock.advance(TICK_MINUTES * MINUTE_SECONDS)
        worker.run_once()
    workshop.clock.advance(TICK_MINUTES * MINUTE_SECONDS)
    return str(job_id)


def test_a_dead_job_pages_once_per_cooldown_and_once_resolved(
    workshop: Workshop,
) -> None:
    worker = workshop.container.gateways.background_worker()
    job_id = kill_one_job(workshop, worker)

    tick_after(workshop, worker, TICK_MINUTES)
    first = alert_texts(workshop)
    wait(workshop, worker, 20)
    within_cooldown = alert_texts(workshop)
    # The admin opens the system page when paged, and comes back later to
    # discard the job: each visit signs in again, since an admin session
    # ends after 15 idle minutes (ADMIN_SESSION_IDLE_TIMEOUT_SECONDS).
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    page = workshop.client.get("/v1/admin/system", headers=bearer(admin_token))
    wait(workshop, worker, 45)
    after_cooldown = alert_texts(workshop)
    admin_token, _ = workshop.sign_in_with_email(ADMIN_EMAIL)
    discarded = workshop.client.post(
        f"/v1/admin/jobs/{job_id}/discard", headers=bearer(admin_token)
    )
    wait(workshop, worker, 10)
    resolved = alert_texts(workshop)

    [firing] = first
    assert firing.startswith("[SEV2] FIRING: ")
    assert "send_owner_digest" in firing
    assert "docs/operations/runbooks/stuck-worker.md" in firing
    assert "https://cabinet.workshop.example/admin/system" in firing
    assert within_cooldown == first
    assert page.status_code == 200, page.text
    [alert] = page.json()["alerts"]
    assert alert["code"] == "dead_jobs" and alert["status"] == "firing"
    assert alert["notification_count"] == 1
    assert page.json()["dead_jobs"] == [{"name": "send_owner_digest", "count": 1}]
    assert len(after_cooldown) == 2
    assert after_cooldown[1].startswith("[SEV2] STILL FIRING: ")
    assert discarded.status_code == 200, discarded.text
    assert len(resolved) == 3
    assert resolved[2].startswith("[SEV2] RESOLVED: ")
