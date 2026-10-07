"""SUPPORT_*: the support contacts read from the environment, forgiving of format."""

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.support_settings_section import (
    read_support_settings,
)


def test_no_support_contact_by_default() -> None:
    support = read_support_settings({})["support"]

    assert support.model_dump(exclude_none=True) == {}


def test_numbers_usernames_and_addresses_are_written_as_people_type_them() -> None:
    support = read_support_settings(
        {
            "SUPPORT_WHATSAPP": " +995 32 2-00 00 00 ",
            "SUPPORT_TELEGRAM": "@workshop_support",
            "SUPPORT_EMAIL": " Help@Workshop.Example ",
        }
    )["support"]

    assert support.whatsapp_number == "+995322000000"
    assert support.telegram_username == "workshop_support"
    assert support.email == "help@workshop.example"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SUPPORT_WHATSAPP", "995322000000"),
        ("SUPPORT_TELEGRAM", "@ab"),
        ("SUPPORT_EMAIL", "help-at-workshop"),
    ],
)
def test_a_wrong_value_names_its_variable(name: str, value: str) -> None:
    with pytest.raises(ValidationFailedError, match=name):
        read_support_settings({name: value})
