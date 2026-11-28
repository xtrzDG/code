"""
A notice to a person about their own account reaches the outbox, although
their request runs in no business's storage scope (Account → Security and
the sign-in are the person's, not a business's): the notice enters each
business's scope itself, since tenant collections refuse unscoped code (on
Postgres, row-level security too). Built on the real container, whose
in-memory collections check the scope as production's do.
"""

from collections.abc import Iterator

import pytest

from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from tests.e2e.harness import Workshop, bearer, start_workshop
from tests.e2e.harness_settings import CABINET_ORIGIN, E2E_ENVIRONMENT
from tests.users.mfa.mfa_api import RESEND_WAIT_SECONDS, set_up_authenticator

OWNER_EMAIL: str = "owner@salobie.example"
PHONE_BROWSER: str = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)


@pytest.fixture
def workshop() -> Iterator[Workshop]:
    workshop = start_workshop({**E2E_ENVIRONMENT, "CABINET_BASE_URL": CABINET_ORIGIN})
    with workshop.client:
        yield workshop


def notices_to(workshop: Workshop, key_prefix: str) -> list[OutboundMessageDocument]:
    """The person's queued notices whose key starts so (any business)."""

    messages = workshop.container.adapters.collections.outbound_message_collection()
    with workshop.container.utilities.storage_scope().platform_wide():
        stored: list[OutboundMessageDocument] = messages.list_all()
    return [
        message
        for message in stored
        if message.kind is OutboundMessageKind.STAFF_NOTIFICATION
        and str(message.idempotency_key).startswith(key_prefix)
    ]


def owner_of_a_restaurant(workshop: Workshop) -> tuple[str, str, str]:
    """An owner who signs in by e-mail: their token, id and business."""

    token, session = workshop.sign_in_with_email(OWNER_EMAIL)
    created = workshop.client.post(
        "/v1/businesses",
        json={"name": "Salobie Bia", "niche_key": "restaurant", "country_code": "GE"},
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    return token, str(session["user"]["id"]), str(created.json()["id"])


def sign_in_from_a_phone(workshop: Workshop) -> None:
    """The owner signs in again, from a browser of another device."""

    workshop.clock.advance(RESEND_WAIT_SECONDS)
    started = workshop.client.post("/v1/auth/otp/start", json={"email": OWNER_EMAIL})
    assert started.status_code == 200, started.text
    verified = workshop.client.post(
        "/v1/auth/otp/verify",
        json={
            "challenge_id": started.json()["challenge_id"],
            "code": str(workshop.otp.codes[-1].code),
        },
        headers={"User-Agent": PHONE_BROWSER},
    )
    assert verified.status_code == 200, verified.text


def test_a_second_factor_added_in_account_security_is_told_by_e_mail(
    workshop: Workshop,
) -> None:
    token, user_id, business_id = owner_of_a_restaurant(workshop)

    set_up_authenticator(workshop, token, OWNER_EMAIL)

    [notice] = notices_to(workshop, f"staff:security_change:{user_id}-")
    assert str(notice.business_id) == business_id
    assert notice.staff_contact is not None
    assert str(notice.staff_contact.address) == OWNER_EMAIL


def test_a_sign_in_from_a_new_device_is_told_by_e_mail(workshop: Workshop) -> None:
    _, _, business_id = owner_of_a_restaurant(workshop)

    sign_in_from_a_phone(workshop)

    [notice] = notices_to(workshop, "staff:sign_in:")
    assert str(notice.business_id) == business_id
    assert notice.staff_contact is not None
    assert str(notice.staff_contact.address) == OWNER_EMAIL
