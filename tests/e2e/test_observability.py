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
        "/api/public/otel/v1/traces"
    ]
    export = json.loads(workshop.langfuse.requests[0].content)
    [span] = export["resourceSpans"][0]["scopeSpans"][0]["spans"]
    attributes = {pair["key"]: pair["value"] for pair in span["attributes"]}
    assert attributes["langfuse.observation.type"] == {"stringValue": "generation"}
    assert attributes["langfuse.observation.model.name"] == {"stringValue": "scripted"}
    # Message texts are not traced by default.
    assert "langfuse.observation.input" not in attributes
    sent_headers = workshop.langfuse.requests[0].headers
    assert sent_headers["authorization"].startswith("Basic ")
    assert sent_headers["x-langfuse-ingestion-version"] == "4"
