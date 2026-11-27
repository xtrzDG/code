"""
The sign-in's second step offers a platform admin held to passkeys
(ADMIN_PASSKEY_REQUIRED) the app's code exactly where the API takes it. An
admin who has a passkey is refused the app's code, so the step leaves the
app out, also while the passkey cannot sign (suspended as a possible copy)
and while this server can offer no passkeys at all (a misconfiguration
production refuses to start with). A recovery code is then the way in.
"""

from collections.abc import Iterator

import pytest
from httpx2 import Response

from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.typings.passkeys.constrained_strings import (
    PasskeyName,
    WebAuthnCredentialId,
    WebAuthnPublicKey,
)
from app.schemas.typings.passkeys.prefixed_id import PasskeyId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.users.mfa.mfa_records import issue_recovery_codes
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import (
    ADMIN_EMAIL,
    CABINET_ORIGIN,
    E2E_ENVIRONMENT,
    JsonObject,
)
from tests.users.mfa.mfa_api import login_code_step, reason_codes, second_step
from tests.users.passkeys.held_admins import admin_id, give_app
from tests.users.passkeys.passkey_api import add_passkey, new_authenticator

HELD_TO_PASSKEYS: dict[str, str] = {**E2E_ENVIRONMENT, "ADMIN_PASSKEY_REQUIRED": "true"}


def open_workshop(environment: dict[str, str]) -> Iterator[Workshop]:
    opened = start_workshop(environment)
    with opened.client:
        yield opened


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    """Passkeys offered: the cabinet's address names the relying party."""

    yield from open_workshop({**HELD_TO_PASSKEYS, "CABINET_BASE_URL": CABINET_ORIGIN})


@pytest.fixture
def workshop_without_passkeys() -> Iterator[Workshop]:
    """No passkey can be offered: a cabinet on an IP address has no relying party."""

    yield from open_workshop(
        {**HELD_TO_PASSKEYS, "CABINET_BASE_URL": "http://127.0.0.1:3000"}
    )


def answer_next_step(
    workshop: Workshop, recovery_code: str
) -> tuple[JsonObject, Response, Response]:
    """The admin's next second step: the app's code, then a recovery code."""

    step = login_code_step(workshop, ADMIN_EMAIL)
    workshop.clock.advance(30)
    app_code = second_step(
        workshop,
        step,
        code=workshop.authenticators.code_for(ADMIN_EMAIL, workshop.clock),
    )
    return step, app_code, second_step(workshop, step, recovery_code=recovery_code)


def test_an_admin_whose_passkey_was_suspended_is_offered_a_recovery_code(
    workshop: Workshop,
) -> None:
    login_code_step(workshop, ADMIN_EMAIL)
    give_app(workshop, admin_id(workshop))
    signed_in = second_step(
        workshop,
        login_code_step(workshop, ADMIN_EMAIL),
        code=workshop.authenticators.code_for(ADMIN_EMAIL, workshop.clock),
    )
    token: str = signed_in.json()["access_token"]
    assert add_passkey(workshop, token, new_authenticator()).status_code == 201
    codes = workshop.client.post("/v1/me/mfa/recovery-codes", headers=bearer(token))
    assert codes.status_code == 200, codes.text
    # A copy of it answered once: it signs nothing more, yet it still counts.
    passkeys = workshop.container.repositories.passkey_repo()
    [passkey] = passkeys.list_for_user(UserId(admin_id(workshop)))
    now = workshop.clock.wall_clock.now_unix()
    assert passkeys.mark_clone_suspected(passkey.id, now) is not None

    step, app_code, recovery = answer_next_step(
        workshop, codes.json()["recovery_codes"][0]
    )

    # The step offers what the API takes: not the app, whose code it refuses.
    assert step["mfa_challenge"]["methods"] == ["recovery_code"]
    assert app_code.status_code == 403
    assert reason_codes(app_code) == ["passkey_required"]
    assert recovery.status_code == 200, recovery.text


def test_while_no_passkey_can_be_offered_the_app_stays_refused_and_unoffered(
    workshop_without_passkeys: Workshop,
) -> None:
    workshop = workshop_without_passkeys
    login_code_step(workshop, ADMIN_EMAIL)
    user_id = UserId(admin_id(workshop))
    give_app(workshop, str(user_id))
    now = workshop.clock.wall_clock.now_unix()
    # Added while the server still offered passkeys.
    assert workshop.container.repositories.passkey_repo().add(
        PasskeyDocument(
            id=PasskeyId(),
            user_id=user_id,
            credential_id=WebAuthnCredentialId("Y3JlZGVudGlhbC0wMDAwMDAx"),
            public_key=WebAuthnPublicKey(
                "cHVibGljLWtleS1vZi1hLXRlc3QtcGFzc2tleS0wMDAwMA"
            ),
            name=PasskeyName("Laptop"),
            created_at=now,
            updated_at=now,
        )
    )
    [code, *_] = issue_recovery_codes(
        workshop.container.repositories.recovery_code_repo(), user_id, now
    )

    step, app_code, recovery = answer_next_step(workshop, str(code))

    assert step["mfa_challenge"]["methods"] == ["recovery_code"]
    assert app_code.status_code == 403
    assert reason_codes(app_code) == ["passkey_required"]
    assert recovery.status_code == 200, recovery.text
