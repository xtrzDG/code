"""Every model call reaches the quality journal (Langfuse) when it is configured."""

import json

from tests.e2e.harness import bearer, start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT

LANGFUSE_ENVIRONMENT: dict[str, str] = {
    **E2E_ENVIRONMENT,
    "LANGFUSE_PUBLIC_KEY": "pk-lf-e2e",
    "LANGFUSE_SECRET_KEY": "sk-lf-e2e",
    "LANGFUSE_HOST": "https://langfuse.test",
}


def test_owner_test_chat_is_traced_and_flushed_by_the_worker_job() -> None:
    workshop = start_workshop(LANGFUSE_ENVIRONMENT)
    with workshop.client as client:
        token, _ = workshop.sign_in_with_phone("+995 555 12 34 56")
        headers = bearer(token)
        business_id = client.post(
            "/v1/businesses",
            json={"name": "Salobie Bia", "niche_key": "restaurant"},
            headers=headers,
        ).json()["id"]
        base = f"/v1/businesses/{business_id}"
        saved = client.put(
            f"{base}/profile/steps/niche_and_languages",
            json={"answers": [{"question_key": "cuisine", "answer": "Грузинская"}]},
            headers=headers,
        )
        assert saved.status_code == 200, saved.text
        assembled = client.post(
            f"{base}/assistant-versions",
            json={"run_autotests": False},
            headers=headers,
        )
        assert assembled.status_code == 201, assembled.text

        answer = client.post(
            f"{base}/test-chat",
            json={"text": "Добрый день"},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
        assert workshop.langfuse.requests == []  # buffered, not sent inline

        worker = workshop.container.gateways.background_worker()
        report = worker.run_once()

    assert report.failures == 0
    assert [request.url.path for request in workshop.langfuse.requests] == [
        "/api/public/ingestion"
    ]
    batch = json.loads(workshop.langfuse.requests[0].content)["batch"]
    assert [event["type"] for event in batch] == ["trace-create", "generation-create"]
    generation = batch[1]["body"]
    assert generation["model"] == "scripted"
    assert "input" not in generation  # message texts are not traced by default
    assert workshop.langfuse.requests[0].headers["authorization"].startswith("Basic ")
