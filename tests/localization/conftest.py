"""Fixtures of the catalog route tests: a client and its business."""

import pytest
from fastapi.testclient import TestClient

from app.schemas.domain.businesses import BusinessDocument
from tests.localization.catalog_routes_client import build_client


@pytest.fixture(name="client_and_business")
def fixture_client_and_business() -> tuple[TestClient, BusinessDocument]:
    return build_client()


@pytest.fixture(name="client")
def fixture_client(
    client_and_business: tuple[TestClient, BusinessDocument],
) -> TestClient:
    return client_and_business[0]
