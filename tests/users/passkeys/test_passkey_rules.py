"""
The rules under passkeys: the relying party the server binds them to
(WEBAUTHN_RP_ID and the cabinet's host), the signature counter of a copied
authenticator, and the derived id and account handle of a passkey.
"""

import base64

import pytest

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.passkeys.constrained_integers import WebAuthnSignCount
from app.schemas.typings.passkeys.constrained_strings import WebAuthnCredentialId
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.security.passkey_identity import passkey_id_for, user_handle_for
from app.utilities.security.passkey_policy import is_sign_count_regressed

CABINET: str = "https://app.workshop.example"


def relying_party(environment: dict[str, str]) -> str | None:
    rp_id = assemble_app_settings(environment).sessions.webauthn_rp_id
    return None if rp_id is None else str(rp_id)


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({"CABINET_BASE_URL": "https://app.workshop.example"}, "app.workshop.example"),
        (
            {
                "CABINET_BASE_URL": "https://app.workshop.example",
                "WEBAUTHN_RP_ID": "Workshop.Example",
            },
            "workshop.example",
        ),
        ({"CABINET_BASE_URL": "http://localhost:4102"}, "localhost"),
        ({"CABINET_BASE_URL": "http://127.0.0.1:4102"}, None),
        ({"CABINET_BASE_URL": "http://[::1]:4102"}, None),
        # Development without a setting: the local cabinet.
        ({}, "localhost"),
    ],
)
def test_passkeys_are_bound_to_the_cabinet_host_or_a_domain_above_it(
    environment: dict[str, str], expected: str | None
) -> None:
    assert relying_party(environment) == expected


@pytest.mark.parametrize(
    "rp_id", ["other.example", "example", "https://workshop.example"]
)
def test_a_relying_party_the_cabinet_does_not_belong_to_is_refused(
    rp_id: str,
) -> None:
    with pytest.raises(ValidationFailedError):
        relying_party({"CABINET_BASE_URL": CABINET, "WEBAUTHN_RP_ID": rp_id})


@pytest.mark.parametrize(
    ("stored", "presented", "regressed"),
    [
        (0, 0, False),  # a synced passkey reports no counter at all
        (0, 1, False),
        (5, 6, False),
        (5, 5, True),  # the copy signs with a counter already used
        (5, 3, True),
        (5, 0, True),  # a counter that stopped counting
    ],
)
def test_a_counter_that_does_not_grow_means_a_copied_authenticator(
    stored: int, presented: int, regressed: bool
) -> None:
    assert (
        is_sign_count_regressed(WebAuthnSignCount(stored), WebAuthnSignCount(presented))
        is regressed
    )


def test_one_credential_is_one_passkey_and_one_person_has_one_handle() -> None:
    credential = WebAuthnCredentialId("Y3JlZGVudGlhbC1vbmUtMDAwMDAw")
    user_id = UserId()

    assert passkey_id_for(credential) == passkey_id_for(credential)
    assert passkey_id_for(credential) != passkey_id_for(
        WebAuthnCredentialId("Y3JlZGVudGlhbC10d28tMDAwMDAw")
    )
    handle = str(user_handle_for(user_id))
    assert handle == str(user_handle_for(user_id))
    assert handle != str(user_handle_for(UserId()))
    # Unpadded base64url of the random user id: no e-mail or phone number.
    assert "=" not in handle
    assert base64.urlsafe_b64decode(handle + "=" * (-len(handle) % 4)).decode() == (
        str(user_id)
    )
