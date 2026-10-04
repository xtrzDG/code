"""
Signing in with and without an authenticator: the login code alone opens
a session only for people without one; the second step takes a fresh
authenticator code or a recovery code, each once.
"""

from app.schemas.typings.mfa.constrained_integers import TotpTimeStep
from app.utilities.security.totp_codes import totp_code_at
from tests.e2e.harness import Workshop, bearer
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.users.mfa.mfa_api import (
    login_code_step,
    mfa_changes,
    reason_codes,
    second_step,
    set_up_authenticator,
    wrong_code_for,
)

OWNER: str = GEORGIAN_OWNER_PHONE


def last_code(workshop: Workshop, identity: str) -> str:
    """The code the harness's authenticator gave last (already accepted)."""

    authenticators = workshop.authenticators
    return str(
        totp_code_at(
            authenticators.secrets[identity],
            TotpTimeStep(authenticators.last_steps[identity]),
        )
    )


def test_without_an_authenticator_the_login_code_opens_a_one_factor_session(
    workshop: Workshop,
) -> None:
    answer = login_code_step(workshop, OWNER)
    me = workshop.client.get("/v1/me", headers=bearer(answer["access_token"]))

    assert "mfa_required" not in answer
    assert answer["auth_level"] == "one_factor"
    assert answer["recovery_codes"] == []
    assert me.json()["auth_level"] == "one_factor"


def test_with_an_authenticator_a_second_step_opens_a_two_factor_session(
    workshop: Workshop,
) -> None:
    token, session = workshop.sign_in_with_phone(OWNER)
    set_up_authenticator(workshop, token, OWNER)
    workshop.clock.advance(60)

    answer = login_code_step(workshop, OWNER)
    verified = second_step(
        workshop, answer, code=workshop.authenticators.code_for(OWNER, workshop.clock)
    )
    me = workshop.client.get("/v1/me", headers=bearer(verified.json()["access_token"]))

    assert answer["mfa_required"] is True
    assert answer["is_new_user"] is False
    assert answer["mfa_challenge"]["requires_enrollment"] is False
    assert answer["mfa_challenge"]["expires_in_seconds"] == 300
    assert "access_token" not in answer
    assert verified.status_code == 200, verified.text
    assert verified.json()["auth_level"] == "two_factor"
    assert verified.json()["user"]["id"] == session["user"]["id"]
    assert me.json()["auth_level"] == "two_factor"
    assert mfa_changes(workshop, session["user"]["id"]) == ["totp_factor"]


def test_a_wrong_or_already_used_authenticator_code_is_refused(
    workshop: Workshop,
) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER)
    set_up_authenticator(workshop, token, OWNER)
    used: str = last_code(workshop, OWNER)
    answer = login_code_step(workshop, OWNER)

    wrong = second_step(workshop, answer, code=wrong_code_for(used))
    # The code that confirmed the authenticator was used: it works once.
    replayed = second_step(workshop, answer, code=used)
    both = second_step(workshop, answer, code=used, recovery_code="abcd-efgh-jkmn")

    assert wrong.status_code == 422
    assert reason_codes(wrong) == ["wrong_code"]
    assert replayed.status_code == 422
    assert reason_codes(replayed) == ["wrong_code"]
    assert both.status_code == 422
    assert reason_codes(both) == []


def test_a_recovery_code_works_once(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER)
    codes = set_up_authenticator(workshop, token, OWNER)

    first = second_step(
        workshop, login_code_step(workshop, OWNER), recovery_code=codes[0]
    )
    again = second_step(
        workshop, login_code_step(workshop, OWNER), recovery_code=codes[0]
    )
    typed = codes[1].replace("-", " ").upper()
    another = second_step(
        workshop, login_code_step(workshop, OWNER), recovery_code=typed
    )
    security = workshop.client.get(
        "/v1/me/security", headers=bearer(another.json()["access_token"])
    )

    assert len(codes) == 10 and len(set(codes)) == 10
    assert first.status_code == 200, first.text
    assert first.json()["auth_level"] == "two_factor"
    assert again.status_code == 422
    assert reason_codes(again) == ["wrong_code"]
    assert another.status_code == 200, another.text
    assert security.json()["recovery_codes_left"] == 8


def test_the_second_step_expires_and_is_used_once(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER)
    set_up_authenticator(workshop, token, OWNER)
    late = login_code_step(workshop, OWNER)
    workshop.clock.advance(301)
    expired = second_step(
        workshop, late, code=workshop.authenticators.code_for(OWNER, workshop.clock)
    )
    answer = login_code_step(workshop, OWNER)
    opened = second_step(
        workshop, answer, code=workshop.authenticators.code_for(OWNER, workshop.clock)
    )
    reused = second_step(
        workshop, answer, code=workshop.authenticators.code_for(OWNER, workshop.clock)
    )

    assert expired.status_code == 401
    assert expired.json()["error"] == "authentication_required"
    assert opened.status_code == 200, opened.text
    assert reused.status_code == 401


def test_five_wrong_codes_lock_the_second_step(workshop: Workshop) -> None:
    token, _ = workshop.sign_in_with_phone(OWNER)
    set_up_authenticator(workshop, token, OWNER)
    answer = login_code_step(workshop, OWNER)
    right: str = workshop.authenticators.code_for(OWNER, workshop.clock)

    wrong = [
        second_step(workshop, answer, code=wrong_code_for(right)).status_code
        for _ in range(5)
    ]
    locked = second_step(workshop, answer, code=right)

    assert wrong == [422] * 5
    assert locked.status_code == 429
