"""Assembling a version over HTTP on the assistant routes."""

from typing import Any

from fastapi.testclient import TestClient


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
