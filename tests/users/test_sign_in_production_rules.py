"""
Sign-in rules production enforces at startup: login codes live ten minutes
at most (OTP_LIFETIME_SECONDS), and platform admins sign in with passkeys
(ADMIN_PASSKEY_REQUIRED, on by default there). Development, tests and the
preview stand are never asked.
"""

import pytest

from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.production.sign_in_requirements import (
    find_sign_in_problems,
)
from tests.platform.production_settings import problems_with, production_with


@pytest.mark.parametrize(
    ("changes", "named"),
    [
        ({"OTP_LIFETIME_SECONDS": "601"}, "OTP_LIFETIME_SECONDS=601"),
        ({"OTP_LIFETIME_SECONDS": "3600"}, "OTP_LIFETIME_SECONDS=3600"),
        ({"ADMIN_PASSKEY_REQUIRED": "false"}, "ADMIN_PASSKEY_REQUIRED=false"),
    ],
)
def test_production_names_a_weak_sign_in_setting(
    changes: dict[str, str], named: str
) -> None:
    [problem] = problems_with(changes)

    assert problem.startswith(named), problem


def test_ten_minutes_and_passkeys_for_admins_pass() -> None:
    settings = assemble_app_settings(production_with({"OTP_LIFETIME_SECONDS": "600"}))

    assert problems_with({"OTP_LIFETIME_SECONDS": "600"}) == []
    assert settings.sessions.is_admin_passkey_required is True


def test_admin_passkeys_need_a_domain_for_passkeys() -> None:
    settings = assemble_app_settings(production_with({}))
    without_passkeys = settings.model_copy(
        update={
            "sessions": settings.sessions.model_copy(update={"webauthn_rp_id": None})
        }
    )

    [problem] = find_sign_in_problems(without_passkeys)

    assert str(problem).startswith("ADMIN_PASSKEY_REQUIRED needs passkeys")


def test_a_missing_cabinet_address_is_named_once() -> None:
    settings = assemble_app_settings(production_with({}))
    without_cabinet = settings.model_copy(
        update={
            "cabinet_base_url": None,
            "sessions": settings.sessions.model_copy(update={"webauthn_rp_id": None}),
        }
    )

    # "CABINET_BASE_URL is not set" (address_requirements.py) says it all.
    assert find_sign_in_problems(without_cabinet) == []


@pytest.mark.parametrize("environment", ["development", "test"])
def test_development_and_tests_may_keep_longer_codes(environment: str) -> None:
    settings = assemble_app_settings(
        {"APP_ENV": environment, "OTP_LIFETIME_SECONDS": "1800"}
    )

    assert int(settings.otp_lifetime_seconds) == 1800
    assert settings.sessions.is_admin_passkey_required is False
