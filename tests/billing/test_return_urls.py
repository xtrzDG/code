"""Pages a payer may be sent back to: the cabinet's origins and the API."""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from app.utilities.billing.return_urls import (
    list_return_origins,
    require_allowed_return_url,
)
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings


def test_the_cabinet_base_url_origin_is_an_allowed_return_origin() -> None:
    settings = assemble_app_settings(
        {
            "APP_ENV": "production",
            "ENCRYPTION_KEY": "return-urls-secret-0123456789abcdef",
            "APP_BASE_URL": "https://api.workshop.example",
            "CABINET_BASE_URL": "https://cabinet.workshop.example/app/",
        }
    )

    assert list_return_origins(settings) == [
        "https://cabinet.workshop.example",
        "https://api.workshop.example",
    ]
    require_allowed_return_url(
        PaymentReturnUrl("https://cabinet.workshop.example/b/business_1/billing"),
        settings,
    )
    with pytest.raises(ValidationFailedError):
        require_allowed_return_url(
            PaymentReturnUrl("https://cabinet.workshop.example.evil.test/billing"),
            settings,
        )


def test_an_origin_listed_twice_is_returned_once() -> None:
    settings = assemble_app_settings(
        {
            "APP_ENV": "test",
            "CORS_ALLOWED_ORIGINS": "http://localhost:3000,https://cabinet.example",
            "CABINET_BASE_URL": "http://localhost:3000",
        }
    )

    assert list_return_origins(settings) == [
        "http://localhost:3000",
        "https://cabinet.example",
    ]


def test_without_cabinet_settings_only_the_api_address_is_allowed() -> None:
    settings = assemble_app_settings(
        {
            "APP_ENV": "production",
            "ENCRYPTION_KEY": "return-urls-secret-0123456789abcdef",
            "APP_BASE_URL": "https://api.workshop.example",
        }
    )

    assert list_return_origins(settings) == ["https://api.workshop.example"]
    with pytest.raises(ValidationFailedError):
        require_allowed_return_url(
            PaymentReturnUrl("http://localhost:3000/billing"), settings
        )
