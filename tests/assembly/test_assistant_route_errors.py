"""Assistant route errors and status codes, and the OpenAPI optional bodies."""

from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from tests.assembly.assistant_routes_helpers import assemble, versions_url
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import seed_italian_restaurant
from tests.assembly.testbed import AssemblyTestbed


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
    testbed.run_worker()
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
