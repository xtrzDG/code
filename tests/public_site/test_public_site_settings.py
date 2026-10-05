"""
PUBLIC_DEMO_BUSINESS_IDS, PUBLIC_DEMO_MESSAGES_PER_HOUR and
LEGAL_TEXTS_FINAL, and the directory of demo businesses they fill.
"""

import pytest

from app.registries.public_site.public_demo_directory_registry import (
    PublicDemoDirectoryRegistry,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

RESTAURANT: str = "business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10"
SALON: str = "business_6a0c1f2e-3b4d-4e5f-8a6b-7c8d9e0f1a2b"
CLINIC: str = "business_1b2c3d4e-5f60-4718-9a2b-3c4d5e6f7a8b"


def test_the_public_site_is_off_and_draft_by_default() -> None:
    settings = assemble_app_settings({}).public_site

    assert settings.demo_business_ids == []
    assert settings.demo_messages_per_hour == 300
    assert settings.are_legal_texts_final is False


def test_demo_businesses_budget_and_final_texts_are_read() -> None:
    settings = assemble_app_settings(
        {
            "PUBLIC_DEMO_BUSINESS_IDS": f"{RESTAURANT}, {SALON}",
            "PUBLIC_DEMO_MESSAGES_PER_HOUR": "1200",
            "LEGAL_TEXTS_FINAL": "true",
        }
    ).public_site

    assert settings.demo_business_ids == [BusinessId(RESTAURANT), BusinessId(SALON)]
    assert settings.demo_messages_per_hour == 1200
    assert settings.are_legal_texts_final is True


@pytest.mark.parametrize(
    "environment",
    [
        {"PUBLIC_DEMO_BUSINESS_IDS": f"{RESTAURANT},{RESTAURANT}"},
        {"PUBLIC_DEMO_BUSINESS_IDS": "restaurant"},
        {"PUBLIC_DEMO_MESSAGES_PER_HOUR": "0"},
        {"PUBLIC_DEMO_MESSAGES_PER_HOUR": "1000000"},
    ],
    ids=["twice", "malformed", "no-budget", "huge-budget"],
)
def test_a_wrong_public_site_setting_stops_the_start(
    environment: dict[str, str],
) -> None:
    with pytest.raises(ValidationFailedError):
        assemble_app_settings(environment)


def test_configured_demos_keep_their_order_and_win_over_seeded_ones() -> None:
    directory = PublicDemoDirectoryRegistry([BusinessId(SALON), BusinessId(RESTAURANT)])

    directory.adopt_seeded([BusinessId(CLINIC)])

    assert directory.list_business_ids() == [BusinessId(SALON), BusinessId(RESTAURANT)]
    assert directory.includes(BusinessId(RESTAURANT))
    assert not directory.includes(BusinessId(CLINIC))


def test_without_configured_demos_the_seeded_businesses_answer_once_each() -> None:
    directory = PublicDemoDirectoryRegistry([])
    assert directory.list_business_ids() == []

    directory.adopt_seeded(
        [BusinessId(RESTAURANT), BusinessId(SALON), BusinessId(RESTAURANT)]
    )

    assert directory.list_business_ids() == [BusinessId(RESTAURANT), BusinessId(SALON)]
    assert directory.includes(BusinessId(SALON))
