"""
The API and the worker run `run_startup_checks` before serving: production
stops on its settings' problems (and without a login code provider, a
usable key ring or the seller's VAT rate) before anything else starts;
development starts as before.
"""

import threading

import pytest
from fastapi.testclient import TestClient

from app.gateways.startup_checks import check_production_requirements
from app.main import build_application
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.worker_main import main as run_worker
from tests.platform.production_settings import container_with, production_with

NO_LOGIN_PROVIDER: dict[str, str | None] = {"SMTP_HOST": None, "SMTP_FROM": None}


def test_a_complete_production_environment_starts() -> None:
    assert check_production_requirements(container_with(production_with({}))) == []


def test_development_is_never_checked() -> None:
    container = container_with({"APP_ENV": "development", "LLM_PROVIDER": "scripted"})

    assert check_production_requirements(container) == []


def test_production_without_a_login_code_provider_is_refused() -> None:
    container = container_with(production_with(NO_LOGIN_PROVIDER))

    with pytest.raises(ValidationFailedError, match="No login code provider"):
        check_production_requirements(container)


def test_production_refuses_the_public_compose_key() -> None:
    container = container_with(
        production_with({"ENCRYPTION_KEY": "local-compose-key-for-this-machine-only"})
    )

    with pytest.raises(ValidationFailedError, match="ENCRYPTION_KEY"):
        check_production_requirements(container)


def test_an_italian_seller_registered_for_vat_starts() -> None:
    registered = production_with(
        {"PLATFORM_VAT_REGISTERED": "true", "SELLER_TAX_ID": "IT12345678901"}
    )

    assert check_production_requirements(container_with(registered)) == []


def test_a_registered_seller_of_a_country_without_a_rate_is_refused() -> None:
    french = production_with(
        {
            "PLATFORM_VAT_REGISTERED": "true",
            "SELLER_TAX_ID": "FR12345678901",
            "SELLER_COUNTRY_CODE": "FR",
            "SELLER_TIME_ZONE": "Europe/Paris",
        }
    )

    with pytest.raises(ValidationFailedError, match="SELLER_COUNTRY_CODE=FR"):
        check_production_requirements(container_with(french))


def test_the_api_does_not_start_on_production_problems() -> None:
    application = build_application(
        container_with(production_with({"LOG_FORMAT": "text"}))
    )

    with (
        pytest.raises(ValidationFailedError, match="LOG_FORMAT"),
        TestClient(application),
    ):
        pass


def test_the_worker_does_not_start_on_production_problems() -> None:
    # Not on the main thread: the worker then installs no signal handlers.
    container = container_with(production_with({"LLM_PROVIDER": "scripted"}))
    raised: list[BaseException] = []

    def start() -> None:
        try:
            run_worker(container, threading.Event())
        except ValidationFailedError as error:
            raised.append(error)

    thread = threading.Thread(target=start)
    thread.start()
    thread.join(timeout=30)

    assert not thread.is_alive()
    [error] = raised
    assert "LLM_PROVIDER=scripted" in str(error)
