"""The API and the container start from the environment alone."""

import os
from collections.abc import Iterator

import pytest
from dependency_injector import containers, providers
from fastapi.testclient import TestClient

from app.containers.app import AppContainer
from app.main import create_application
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.harness import start_workshop
from tests.e2e.harness_settings import E2E_ENVIRONMENT
from tests.e2e.workshop_container import replace_provider

OPTIONAL_PROVIDERS: frozenset[str] = frozenset(
    {
        "clients.postgres_pool",
        "clients.flitt_client",
        "clients.langfuse_ingestion_client",
        "clients.twilio_messaging_client",
        "clients.telegram_gateway_client",
        "clients.whatsapp_authentication_client",
        "clients.smtp_email_client",
        "clients.turnstile_verification_client",
        "clients.object_storage_client",
        "clients.web_push_client",
        # In memory there is no transaction to group writes in.
        "adapters.processes.storage_read_session",
        "adapters.processes.storage_unit_of_work",
        "adapters.storage_read_session",
        "adapters.storage_unit_of_work",
    }
)


@pytest.fixture
def empty_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for variable in list(os.environ):
        monkeypatch.delenv(variable)

    yield


@pytest.mark.usefixtures("empty_environment")
def test_application_boots_with_an_empty_environment() -> None:
    application = create_application()

    with TestClient(application) as client:
        health = client.get("/healthz")
        countries = client.get("/v1/catalog/countries/ge")
        anonymous = client.get("/v1/me")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert countries.status_code == 200
    assert countries.json()["profile"]["currency_code"] == "GEL"
    assert anonymous.status_code == 401


@pytest.mark.usefixtures("empty_environment")
def test_openapi_document_describes_every_module() -> None:
    with TestClient(create_application()) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    paths: dict[str, object] = response.json()["paths"]
    expected_paths = {
        "/v1/auth/otp/start",
        "/v1/me",
        "/v1/businesses",
        "/v1/businesses/{business_id}/dpa",
        "/v1/catalog/countries",
        "/v1/catalog/niches",
        "/v1/businesses/{business_id}/profile/steps/{step}",
        "/v1/businesses/{business_id}/knowledge",
        "/v1/businesses/{business_id}/knowledge/import",
        "/v1/businesses/{business_id}/resources",
        "/v1/businesses/{business_id}/bookings",
        "/v1/businesses/{business_id}/dashboard",
        "/v1/businesses/{business_id}/conversations",
        "/v1/businesses/{business_id}/test-chat",
        "/v1/businesses/{business_id}/assistant-versions",
        "/v1/businesses/{business_id}/channels",
        "/v1/channels/meta/webhook",
        "/v1/widget/{business_id}/messages",
        "/v1/voice/webhooks/post-call",
        "/v1/businesses/{business_id}/billing",
        "/v1/payments/flitt/webhook",
        "/v1/admin/clients",
    }
    assert expected_paths <= set(paths)


def resolve_every_provider(
    container: containers.Container,
    prefix: str,
    resolved: list[str],
) -> None:
    """Call every provider of `container`, descending into child containers."""

    for provider_name, provider in container.providers.items():
        if isinstance(provider, providers.DependenciesContainer):
            continue

        name = f"{prefix}.{provider_name}"
        if isinstance(provider, providers.Container):
            resolve_every_provider(provider(), name, resolved)
            continue

        instance: object = provider()
        # Optional clients are None until their settings are present.
        assert instance is not None or name in OPTIONAL_PROVIDERS, name
        resolved.append(name)


def test_every_provider_of_the_container_resolves() -> None:
    container = AppContainer()
    replace_provider(
        container.config.app_settings,
        assemble_app_settings(E2E_ENVIRONMENT),
    )
    resolved: list[str] = []
    for container_name, child_provider in container.providers.items():
        resolve_every_provider(child_provider(), container_name, resolved)

    assert len(resolved) > 400
    assert "operators.channels.widget_message_operator" in resolved
    assert "gateways.background_worker" in resolved


def test_stateful_collaborators_are_shared_singletons() -> None:
    workshop = start_workshop()
    container = workshop.container

    assert (
        container.pipelines.conversations.customer_message_pipeline()
        is container.pipelines.conversations.customer_message_pipeline()
    )
    assert (
        container.registries.business_lock_registry()
        is container.registries.business_lock_registry()
    )
    assert (
        container.use_cases.channels.create_telegram_link_use_case()
        is container.use_cases.channels.create_telegram_link_use_case()
    )
    assert container.adapters.collections.booking_collection() is (
        container.adapters.collections.booking_collection()
    )
