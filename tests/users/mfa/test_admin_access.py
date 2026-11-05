"""
Platform admins: an authenticator is set up at the first sign-in, the
admin pages refuse sessions without two factors, and admin rights come
from the PLATFORM_ADMIN_* lists at every request, never from the stored
flag.
"""

from app.schemas.constants.mfa import AuthLevel
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import ADMIN_EMAIL
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.users.mfa.mfa_api import (
    login_code_step,
    reason_codes,
    second_step,
    store_session,
)

CLIENTS_URL: str = "/v1/admin/clients"


def test_an_admin_sets_up_an_authenticator_at_the_first_sign_in(
    workshop: Workshop,
) -> None:
    answer = login_code_step(workshop, ADMIN_EMAIL)
    challenge_id: str = answer["mfa_challenge"]["mfa_challenge_id"]
    without_app = second_step(workshop, answer, code="123456")
    enrolled = workshop.client.post(
        "/v1/auth/mfa/enroll", json={"mfa_challenge_id": challenge_id}
    )
    workshop.authenticators.secrets[ADMIN_EMAIL] = enrolled.json()["secret"]
    verified = second_step(
        workshop,
        answer,
        code=workshop.authenticators.code_for(ADMIN_EMAIL, workshop.clock),
    )
    clients = workshop.client.get(
        CLIENTS_URL, headers=bearer(verified.json()["access_token"])
    )

    assert answer["mfa_required"] is True
    assert answer["mfa_challenge"]["requires_enrollment"] is True
    assert without_app.status_code == 422
    assert enrolled.status_code == 200, enrolled.text
    assert enrolled.json()["issuer"] == "Assistant Workshop"
    assert enrolled.json()["account_label"] == ADMIN_EMAIL
    assert enrolled.json()["provisioning_uri"].startswith(
        "otpauth://totp/Assistant%20Workshop:admin%40workshop.example?secret="
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["auth_level"] == "two_factor"
    assert len(verified.json()["recovery_codes"]) == 10
    assert clients.status_code == 200, clients.text


def test_the_enrollment_step_is_only_for_people_without_an_authenticator(
    workshop: Workshop,
) -> None:
    workshop.sign_in_with_email(ADMIN_EMAIL)
    answer = login_code_step(workshop, ADMIN_EMAIL)
    again = workshop.client.post(
        "/v1/auth/mfa/enroll",
        json={"mfa_challenge_id": answer["mfa_challenge"]["mfa_challenge_id"]},
    )

    assert answer["mfa_challenge"]["requires_enrollment"] is False
    assert again.status_code == 409


def test_admin_pages_refuse_a_session_without_two_factors(
    workshop: Workshop,
) -> None:
    _, session = workshop.sign_in_with_email(ADMIN_EMAIL)
    admin_id: str = session["user"]["id"]
    one_factor = store_session(
        workshop, admin_id, "one-factor-0000", AuthLevel.ONE_FACTOR
    )
    # A session from before two-factor sign-in carries no level at all.
    older = store_session(workshop, admin_id, "older-session-0000", None)

    refused = workshop.client.get(CLIENTS_URL, headers=one_factor)
    refused_older = workshop.client.get(CLIENTS_URL, headers=older)
    me = workshop.client.get("/v1/me", headers=one_factor)

    assert refused.status_code == 403
    assert reason_codes(refused) == ["mfa_required"]
    assert refused_older.status_code == 403
    assert reason_codes(refused_older) == ["mfa_required"]
    # Outside the admin pages the session still works.
    assert me.status_code == 200
    assert me.json()["user"]["is_platform_admin"] is True


def test_the_stored_admin_flag_grants_nothing(workshop: Workshop) -> None:
    token, session = workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)
    users = workshop.container.repositories.user_repo()
    stored = users.get(session["user"]["id"])
    assert stored is not None
    users.save(stored.model_copy(update={"is_platform_admin": True}))

    clients = workshop.client.get(CLIENTS_URL, headers=bearer(token))
    me = workshop.client.get("/v1/me", headers=bearer(token))

    assert clients.status_code == 403
    assert reason_codes(clients) == []
    assert me.json()["user"]["is_platform_admin"] is False
