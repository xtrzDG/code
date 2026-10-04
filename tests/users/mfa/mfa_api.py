"""
Steps of the two-factor tests over the real API: the login code step
alone, setting up an authenticator in Account → Security, sessions made
before two-factor sign-in existed, and reading refusals.
"""

from typing import Any

from httpx2 import Response
from typed_time_provider import Microseconds

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.mfa import AuthLevel
from app.schemas.domain.users import UserSessionDocument
from app.schemas.typings.mfa.constrained_strings import TotpSecret
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import AccessToken
from app.utilities.security.access_tokens import hash_access_token
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import JsonObject

DAY_MICROSECONDS: int = 24 * 3600 * 1_000_000
STEP_UP_SECONDS: int = 600
# A new login code to the same address waits this long (resend throttle).
RESEND_WAIT_SECONDS: int = 31


def login_code_step(workshop: Workshop, identity: str) -> JsonObject:
    """The answer of /v1/auth/otp/verify alone (a session or the second step)."""

    body: dict[str, str] = (
        {"email": identity} if "@" in identity else {"phone_number": identity}
    )
    workshop.clock.advance(RESEND_WAIT_SECONDS)
    started = workshop.client.post("/v1/auth/otp/start", json=body)
    assert started.status_code == 200, started.text
    verified = workshop.client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": started.json()["challenge_id"],
            "code": str(workshop.otp.codes[-1].code),
        },
    )
    assert verified.status_code == 200, verified.text
    answer: JsonObject = verified.json()
    return answer


def second_step(workshop: Workshop, answer: JsonObject, **codes: str) -> Response:
    """POST /v1/auth/mfa/verify for the challenge of a login code step."""

    return workshop.client.post(
        "/v1/auth/mfa/verify",
        json={"mfa_challenge_id": answer["mfa_challenge"]["mfa_challenge_id"], **codes},
    )


def set_up_authenticator(workshop: Workshop, token: str, identity: str) -> list[str]:
    """Account → Security: a new authenticator; returns its recovery codes."""

    started = workshop.client.post("/v1/me/mfa/totp", headers=bearer(token))
    assert started.status_code == 200, started.text
    workshop.authenticators.secrets[identity] = TotpSecret(
        str(started.json()["secret"])
    )
    confirmed = workshop.client.post(
        "/v1/me/mfa/totp/confirm",
        json={"code": workshop.authenticators.code_for(identity, workshop.clock)},
        headers=bearer(token),
    )
    assert confirmed.status_code == 200, confirmed.text
    return [str(code) for code in confirmed.json()["recovery_codes"]]


def wrong_code_for(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


def store_session(
    workshop: Workshop,
    user_id: str,
    token: str,
    auth_level: AuthLevel | None,
) -> dict[str, str]:
    """A session as stored before this release (or with one factor)."""

    now: int = int(workshop.clock.wall_clock.now_unix())
    workshop.container.repositories.user_session_repo().save(
        UserSessionDocument(
            user_id=UserId(user_id),
            token_hash=hash_access_token(AccessToken(token)),
            expires_at=Microseconds(now + DAY_MICROSECONDS),
            auth_level=auth_level,
            authenticated_at=None if auth_level is None else Microseconds(now),
        )
    )
    return bearer(token)


def reason_codes(response: Response) -> list[str]:
    body: dict[str, Any] = response.json()
    return [str(reason["code"]) for reason in body.get("reasons", [])]


def mfa_changes(workshop: Workshop, user_id: str) -> list[str]:
    """The entities of the user's MFA_CHANGED audit entries, oldest first."""

    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    return [
        str(entry.entity)
        for entry in entries.list_all()
        if entry.action is AuditAction.MFA_CHANGED and str(entry.actor_id) == user_id
    ]
