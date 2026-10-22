"""
Steps of the passkey tests over the real API: adding a passkey in Account
→ Security, the passkey answer of a sign-in's second step, and step-up.
"""

from httpx2 import Response

from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from tests.e2e.harness import Workshop, bearer
from tests.e2e.harness_settings import CABINET_ORIGIN, JsonObject
from tests.users.mfa.mfa_api import login_code_step
from tests.users.passkeys.software_authenticator import SoftwareAuthenticator

OWNER_EMAIL: str = "owner@cafe.example"


def new_authenticator(*, counts_signatures: bool = True) -> SoftwareAuthenticator:
    return SoftwareAuthenticator(
        origin=CABINET_ORIGIN, counts_signatures=counts_signatures
    )


def add_passkey(
    workshop: Workshop,
    token: str,
    authenticator: SoftwareAuthenticator,
    name: str | None = None,
) -> Response:
    """Account → Security: options, the authenticator's answer, the result."""

    started = workshop.client.post(
        "/v1/me/passkeys/registration", headers=bearer(token)
    )
    assert started.status_code == 200, started.text
    body: JsonObject = {
        "passkey_challenge_id": started.json()["passkey_challenge_id"],
        "credential": authenticator.register(started.json()["options"]),
    }
    if name is not None:
        body["name"] = name
    return workshop.client.post("/v1/me/passkeys", json=body, headers=bearer(token))


def sign_up_with_passkey(
    workshop: Workshop, authenticator: SoftwareAuthenticator, email: str = OWNER_EMAIL
) -> tuple[str, JsonObject]:
    """A new owner who added a passkey: their session token and the answer."""

    token, _ = workshop.sign_in_with_email(email)
    added = add_passkey(workshop, token, authenticator)
    assert added.status_code == 201, added.text
    added_body: JsonObject = added.json()
    return token, added_body


def passkey_options(workshop: Workshop, step: JsonObject) -> Response:
    return workshop.client.post(
        "/v1/auth/mfa/passkey/options",
        json={"mfa_challenge_id": step["mfa_challenge"]["mfa_challenge_id"]},
    )


def answer_with_passkey(
    workshop: Workshop,
    step: JsonObject,
    authenticator: SoftwareAuthenticator,
    *,
    origin: str | None = None,
) -> Response:
    """The second step answered by the authenticator."""

    options = passkey_options(workshop, step)
    assert options.status_code == 200, options.text
    return workshop.client.post(
        "/v1/auth/mfa/passkey/verify",
        json={
            "mfa_challenge_id": step["mfa_challenge"]["mfa_challenge_id"],
            "passkey_challenge_id": options.json()["passkey_challenge_id"],
            "credential": authenticator.sign(options.json()["options"], origin=origin),
        },
    )


def sign_in_with_passkey(
    workshop: Workshop, authenticator: SoftwareAuthenticator, email: str = OWNER_EMAIL
) -> Response:
    return answer_with_passkey(
        workshop, login_code_step(workshop, email), authenticator
    )


def audit_entries(workshop: Workshop, user_id: str) -> list[AuditLogEntryDocument]:
    entries = workshop.container.adapters.collections.audit_log_entry_collection()
    return [entry for entry in entries.list_all() if str(entry.actor_id) == user_id]


def mfa_change_references(workshop: Workshop, user_id: str) -> list[str]:
    return [
        str(entry.entity_id)
        for entry in audit_entries(workshop, user_id)
        if entry.action is AuditAction.MFA_CHANGED
    ]
