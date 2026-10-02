"""The background worker inside the API process (EMBEDDED_WORKER)."""

import threading
import time

from app.main import EMBEDDED_WORKER_THREAD_NAME
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.journeys import (
    WIZARD_STEPS,
    JsonObject,
    sign_in_and_create_restaurant,
)

# The queue is polled every second, so a run starts within a second of
# being queued; the scripted model plays it in well under a second.
EMBEDDED_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "EMBEDDED_WORKER": "true",
    "WORKER_POLL_SECONDS": "1",
}
WAIT_SECONDS: float = 30.0


def embedded_worker_threads() -> list[threading.Thread]:
    return [
        thread
        for thread in threading.enumerate()
        if thread.name == EMBEDDED_WORKER_THREAD_NAME
    ]


def test_the_lifespan_starts_the_worker_and_stops_it_on_shutdown() -> None:
    workshop = start_workshop(EMBEDDED_ENVIRONMENT)
    assert embedded_worker_threads() == []

    with workshop.client:
        running = embedded_worker_threads()
        assert len(running) == 1
        assert running[0].is_alive()
        assert running[0].daemon

    assert not running[0].is_alive()
    assert embedded_worker_threads() == []


def test_without_the_setting_the_api_starts_no_worker() -> None:
    workshop = start_workshop()

    with workshop.client:
        assert embedded_worker_threads() == []


def wait_for_finished_run(
    workshop: Workshop,
    base: str,
    version_id: str,
    headers: dict[str, str],
) -> JsonObject:
    deadline: float = time.monotonic() + WAIT_SECONDS
    while True:
        response = workshop.client.get(
            f"{base}/assistant-versions/{version_id}/autotest-run", headers=headers
        )
        assert response.status_code == 200, response.text
        run: JsonObject = response.json()
        if run["status"] != "running" or time.monotonic() > deadline:
            return run

        time.sleep(0.05)


def test_a_queued_autotest_run_finishes_inside_the_api() -> None:
    workshop = start_workshop(EMBEDDED_ENVIRONMENT)
    with workshop.client:
        client = workshop.client
        token, _, business_id = sign_in_and_create_restaurant(workshop)
        headers = bearer(token)
        base = f"/v1/businesses/{business_id}"
        for step, body in WIZARD_STEPS.items():
            saved = client.put(
                f"{base}/profile/steps/{step}", json=body, headers=headers
            )
            assert saved.status_code == 200, (step, saved.text)

        contacts = client.patch(
            base,
            json={
                "manager_contacts": [
                    {
                        "name": "Гиорги",
                        "channel": "telegram",
                        "address": "70001",
                        "language": "ru",
                    }
                ]
            },
            headers=headers,
        )
        assert contacts.status_code == 200, contacts.text
        # Assembling queues the autotests; nobody calls the worker by hand.
        assembled = client.post(f"{base}/assistant-versions", json={}, headers=headers)
        assert assembled.status_code == 201, assembled.text
        assert assembled.json()["status"] == "testing"
        version_id = str(assembled.json()["id"])

        run = wait_for_finished_run(workshop, base, version_id, headers)

    assert run["status"] == "finished"
    assert run["is_passed"] is True
    assert run["is_full_coverage"] is True
    assert run["version_status"] == "ready"
    assert workshop.model.judge_calls == run["scenario_count"]
