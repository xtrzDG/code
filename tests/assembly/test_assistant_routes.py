from typing import Any

from fastapi.testclient import TestClient

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from tests.assembly.builders import seed_georgian_restaurant, seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed


def versions_url(business_id: object) -> str:
    return f"/v1/businesses/{business_id}/assistant-versions"


def assemble(
    client: TestClient,
    headers: dict[str, str],
    business_id: object,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.post(versions_url(business_id), headers=headers, json=body)
    assert response.status_code == 201, response.text
    version: dict[str, Any] = response.json()
    return version


def test_owner_assembles_tests_publishes_and_rolls_back_over_http() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    base = versions_url(business.id)

    draft = assemble(client, owner, business.id, {"run_autotests": False})
    assert draft["version_number"] == 1
    assert draft["status"] == "draft"
    assert draft["prompt_text"].startswith("# Role\n")
    assert draft["facts"][0] == {
        "key": "business_name",
        "label": "Business name",
        "value": "Café Rustaveli",
    }
    assert "send_link" in draft["tools"]

    tested = client.post(f"{base}/{draft['id']}/autotests", headers=owner)
    assert tested.status_code == 200, tested.text
    run: dict[str, Any] = tested.json()
    assert run["version_status"] == "ready"
    assert run["is_passed"] is True
    assert run["scenario_count"] == 29
    assert run["results"][0]["transcript"][0]["author"] == "customer"

    latest_run = client.get(f"{base}/{draft['id']}/autotest-run", headers=owner)
    assert latest_run.status_code == 200
    assert latest_run.json()["id"] == run["id"]

    published = client.post(f"{base}/{draft['id']}/publish", headers=owner)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["voice_agent_id"] == "agent_1"

    second = assemble(client, owner, business.id)
    assert second["status"] == "ready"
    assert second["test_score"] == 5.0
    assert client.post(f"{base}/{second['id']}/publish", headers=owner).json()[
        "status"
    ] == ("published")

    rolled_back = client.post(f"{base}/{draft['id']}/rollback", headers=owner)
    assert rolled_back.status_code == 200, rolled_back.text
    assert rolled_back.json()["status"] == "published"

    history = client.get(base, headers=owner)
    assert history.status_code == 200
    assert [(item["version_number"], item["status"]) for item in history.json()] == [
        (2, "archived"),
        (1, "published"),
    ]
    assert "prompt_text" not in history.json()[0]

    details = client.get(f"{base}/{second['id']}", headers=owner)
    assert details.status_code == 200
    assert details.json()["prompt_text"] == second["prompt_text"]


def test_autotests_can_be_narrowed_over_http() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)

    version = assemble(
        client,
        owner,
        business.id,
        {"languages": ["en"], "kinds": ["human_request", "price_question"]},
    )
    run = client.get(
        f"{versions_url(business.id)}/{version['id']}/autotest-run",
        headers=owner,
    ).json()

    assert [result["scenario_key"] for result in run["results"]] == [
        "price_question__en",
        "human_request__en",
        "price_question__en__1",
        "price_question__en__2",
    ]
    rerun = client.post(
        f"{versions_url(business.id)}/{version['id']}/autotests",
        headers=owner,
        json={"languages": ["it"], "kinds": ["rude_customer"]},
    )
    assert rerun.status_code == 200
    assert [result["scenario_key"] for result in rerun.json()["results"]] == [
        "rude_customer__it"
    ]


def test_failed_version_is_published_only_by_an_admin_with_acceptance() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)
    testbed.judge_raw_answers["booking__it"] = "not a verdict"
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    admin = testbed.bearer(testbed.add_platform_admin())
    version = assemble(client, owner, business.id)
    publish_url = f"{versions_url(business.id)}/{version['id']}/publish"

    refused = client.post(publish_url, headers=owner)
    forced_by_owner = client.post(
        publish_url,
        headers=owner,
        json={"accept_failed_tests": True},
    )
    accepted = client.post(
        publish_url,
        headers=admin,
        json={"accept_failed_tests": True},
    )

    assert version["status"] == "tests_failed"
    assert refused.status_code == 409
    assert refused.json()["error"] == "conflict"
    assert forced_by_owner.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "published"


def test_routes_report_errors_with_status_codes() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    other_business = seed_italian_restaurant(testbed)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    staff = testbed.bearer(testbed.staff_id)
    stranger = testbed.bearer(testbed.stranger_id)
    base = versions_url(business.id)
    version = assemble(client, owner, business.id, {"run_autotests": False})
    foreign = assemble(client, owner, other_business.id, {"run_autotests": False})

    responses = {
        "no token": client.get(base),
        "bad token": client.get(base, headers={"Authorization": "Bearer nope"}),
        "malformed business": client.get(
            versions_url("not-a-business"),
            headers=owner,
        ),
        "malformed version": client.get(f"{base}/not-a-version", headers=owner),
        "unknown version": client.get(
            f"{base}/{AssistantVersionId()}",
            headers=owner,
        ),
        "foreign version": client.get(f"{base}/{foreign['id']}", headers=owner),
        "stranger": client.get(base, headers=stranger),
        "staff assembles": client.post(base, headers=staff, json={}),
        "staff tests": client.post(f"{base}/{version['id']}/autotests", headers=staff),
        "staff publishes": client.post(
            f"{base}/{version['id']}/publish", headers=staff
        ),
        "staff rolls back": client.post(
            f"{base}/{version['id']}/rollback",
            headers=staff,
        ),
        "no run yet": client.get(f"{base}/{version['id']}/autotest-run", headers=owner),
        "bad body": client.post(base, headers=owner, json={"run_autotests": "yes"}),
        "unknown field": client.post(base, headers=owner, json={"model": "gpt"}),
        "unknown language": client.post(
            base,
            headers=owner,
            json={"languages": ["de"]},
        ),
        "not json": client.post(
            base,
            headers={**owner, "Content-Type": "application/json"},
            content=b"{oops",
        ),
        "draft publish": client.post(f"{base}/{version['id']}/publish", headers=owner),
        "draft rollback": client.post(
            f"{base}/{version['id']}/rollback",
            headers=owner,
        ),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        "no token": 401,
        "bad token": 401,
        "malformed business": 404,
        "malformed version": 404,
        "unknown version": 404,
        "foreign version": 404,
        "stranger": 404,
        "staff assembles": 403,
        "staff tests": 403,
        "staff publishes": 403,
        "staff rolls back": 403,
        "no run yet": 404,
        "bad body": 422,
        "unknown field": 422,
        "unknown language": 422,
        "not json": 422,
        "draft publish": 409,
        "draft rollback": 409,
    }
    assert responses["no token"].headers["WWW-Authenticate"] == "Bearer"
    staff_read = client.get(f"{base}/{version['id']}", headers=staff)
    assert staff_read.status_code == 200


def test_voice_provider_failure_is_a_bad_gateway() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    client = testbed.build_client()
    owner = testbed.bearer(testbed.owner_id)
    version = assemble(client, owner, business.id)
    testbed.voice_provisioner.error = ExternalServiceError("Voice platform is down.")

    response = client.post(
        f"{versions_url(business.id)}/{version['id']}/publish",
        headers=owner,
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": "external_service_error",
        "message": "Voice platform is down.",
    }


def test_openapi_documents_optional_bodies() -> None:
    testbed = AssemblyTestbed()
    schema = testbed.build_client().get("/openapi.json").json()
    paths = schema["paths"]
    assemble_operation = paths["/v1/businesses/{business_id}/assistant-versions"][
        "post"
    ]
    publish_operation = paths[
        "/v1/businesses/{business_id}/assistant-versions/{version_id}/publish"
    ]["post"]

    assert assemble_operation["requestBody"]["required"] is False
    assert "run_autotests" in str(assemble_operation["requestBody"])
    assert "accept_failed_tests" in str(publish_operation["requestBody"])
    assert (
        "/v1/businesses/{business_id}/assistant-versions/{version_id}/rollback" in paths
    )
