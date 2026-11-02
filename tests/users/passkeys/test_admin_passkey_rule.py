"""
Platform admins on passkeys (ADMIN_PASSKEY_REQUIRED, on by default in
production): a new admin sets up a passkey (never the app), an admin with
a passkey answers with it (never the app's code, a recovery code stays the
way back in), and an admin who has only the app signs in but finds the
admin pages closed until a passkey is added in Account → Security.
Development and tests keep the app (the setting is off there).
"""

from collections.abc import Iterator

import pytest

from app.schemas.constants.mfa import TotpFactorStatus
from app.schemas.domain.mfa import TotpFactorDocument
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.totp_codes import generate_totp_secret
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import ADMIN_EMAIL, CABINET_ORIGIN, E2E_ENVIRONMENT
from tests.users.mfa.mfa_api import login_code_step, reason_codes, second_step
from tests.users.passkeys.passkey_api import add_passkey, new_authenticator

CLIENTS_URL: str = "/v1/admin/clients"


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    opened = start_workshop(
        {
            **E2E_ENVIRONMENT,
            "CABINET_BASE_URL": CABINET_ORIGIN,
            "ADMIN_PASSKEY_REQUIRED": "true",
        }
    )
    with opened.client:
        yield opened


def give_app(workshop: Workshop, user_id: str) -> None:
    """An authenticator app that is on (set up before passkeys were required)."""

    secret = generate_totp_secret()
    workshop.authenticators.secrets[ADMIN_EMAIL] = secret
    now = workshop.clock.wall_clock.now_unix()
    workshop.container.repositories.totp_factor_repo().save(
        TotpFactorDocument(
            user_id=UserId(user_id),
            sealed_secret=workshop.container.adapters.totp_secret_cipher().seal(secret),
            status=TotpFactorStatus.ACTIVE,
            confirmed_at=now,
            created_at=now,
            updated_at=now,
        )
    )


def admin_id(workshop: Workshop) -> str:
    admin = workshop.container.repositories.user_repo().find_by_email(ADMIN_EMAIL)
    assert admin is not None
    return str(admin.id)


def test_a_new_admin_sets_up_a_passkey_never_the_app(workshop: Workshop) -> None:
    step = login_code_step(workshop, ADMIN_EMAIL)
    app = workshop.client.post(
        "/v1/auth/mfa/enroll",
        json={"mfa_challenge_id": step["mfa_challenge"]["mfa_challenge_id"]},
    )

    assert step["mfa_challenge"]["requires_enrollment"] is True
    assert step["mfa_challenge"]["enrollment_methods"] == ["passkey"]
    assert app.status_code == 403
    assert reason_codes(app) == ["passkey_required"]


def test_an_admin_with_only_the_app_adds_a_passkey_before_the_admin_pages(
    workshop: Workshop,
) -> None:
    login_code_step(workshop, ADMIN_EMAIL)
    give_app(workshop, admin_id(workshop))
    step = login_code_step(workshop, ADMIN_EMAIL)
    signed_in = second_step(
        workshop,
        step,
        code=workshop.authenticators.code_for(ADMIN_EMAIL, workshop.clock),
    )
    token: str = signed_in.json()["access_token"]
    closed = workshop.client.get(CLIENTS_URL, headers=bearer(token))
    added = add_passkey(workshop, token, new_authenticator())
    opened = workshop.client.get(CLIENTS_URL, headers=bearer(token))

    assert step["mfa_challenge"]["methods"] == ["totp"]
    assert signed_in.status_code == 200, signed_in.text
    assert signed_in.json()["auth_level"] == "two_factor"
    assert closed.status_code == 403
    assert reason_codes(closed) == ["passkey_required"]
    assert added.status_code == 201, added.text
    assert opened.status_code == 200, opened.text


def test_an_admin_with_a_passkey_cannot_answer_with_the_app(
    workshop: Workshop,
) -> None:
    login_code_step(workshop, ADMIN_EMAIL)
    give_app(workshop, admin_id(workshop))
    step = login_code_step(workshop, ADMIN_EMAIL)
    token = second_step(
        workshop,
        step,
        code=workshop.authenticators.code_for(ADMIN_EMAIL, workshop.clock),
    ).json()["access_token"]
    recovery_codes = add_passkey(workshop, token, new_authenticator()).json()
    codes = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token))

    next_step = login_code_step(workshop, ADMIN_EMAIL)
    workshop.clock.advance(30)
    app_code = second_step(
        workshop,
        next_step,
        code=workshop.authenticators.code_for(ADMIN_EMAIL, workshop.clock),
    )
    recovery = second_step(
        workshop, next_step, recovery_code=codes.json()["recovery_codes"][0]
    )

    assert recovery_codes["passkey"]["name"]
    assert next_step["mfa_challenge"]["methods"] == ["passkey", "recovery_code"]
    assert app_code.status_code == 403
    assert reason_codes(app_code) == ["passkey_required"]
    # The way back in after a lost passkey.
    assert recovery.status_code == 200, recovery.text
    assert recovery.json()["auth_level"] == "two_factor"


def test_owners_are_never_held_to_passkeys(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone("+995 555 12 34 56")
    started = workshop.client.post("/v1/me/mfa/totp", headers=bearer(token))

    assert started.status_code == 200, started.text


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({}, False),
        ({"APP_ENV": "test"}, False),
        ({"ADMIN_PASSKEY_REQUIRED": "1"}, True),
    ],
)
def test_development_and_tests_keep_the_app_by_default(
    environment: dict[str, str], expected: bool
) -> None:
    settings = assemble_app_settings(environment)

    assert settings.sessions.is_admin_passkey_required is expected
