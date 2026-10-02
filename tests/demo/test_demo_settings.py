"""SEED_DEMO_DATA is a development switch: off by default, refused in production."""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings_assembler import assemble_app_settings


def test_demo_data_is_off_by_default() -> None:
    assert assemble_app_settings({}).is_demo_data_seeding_enabled is False


@pytest.mark.parametrize("environment", ["development", "test"])
def test_demo_data_can_be_switched_on_outside_production(environment: str) -> None:
    settings = assemble_app_settings({"APP_ENV": environment, "SEED_DEMO_DATA": "true"})

    assert settings.is_demo_data_seeding_enabled is True


def test_production_refuses_demo_data() -> None:
    with pytest.raises(ValidationFailedError, match="SEED_DEMO_DATA"):
        assemble_app_settings({"APP_ENV": "production", "SEED_DEMO_DATA": "true"})


def test_production_accepts_the_switch_turned_off() -> None:
    settings = assemble_app_settings({"APP_ENV": "production", "SEED_DEMO_DATA": "no"})

    assert settings.is_demo_data_seeding_enabled is False


def test_a_value_that_is_not_a_boolean_is_refused() -> None:
    with pytest.raises(ValidationFailedError, match="SEED_DEMO_DATA"):
        assemble_app_settings({"SEED_DEMO_DATA": "maybe"})
