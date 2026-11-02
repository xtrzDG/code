"""
Settings → Calls: the recording (off unless the owner turns it on) and
the owner's confirmation of the staff notice that transfers to staff need.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.constants.niches import NicheKey
from app.schemas.domain.profiles import BusinessContacts, BusinessProfileDocument
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from tests.calls.calls_http import build_calls_http_client
from tests.channels.channels_payloads import bearer
from tests.channels.voice_setup import VoiceSetup, build_voice_setup

SWITCHES: dict[str, Any] = {
    "is_summary_enabled": True,
    "is_text_back_enabled": False,
    "is_sms_fallback_enabled": True,
}


@pytest.fixture
def setup() -> VoiceSetup:
    return build_voice_setup()


@pytest.fixture
def client(setup: VoiceSetup) -> TestClient:
    return build_calls_http_client(setup.testbed)


def path(setup: VoiceSetup) -> str:
    return f"/v1/businesses/{setup.business.id}/call-settings"


def put(client: TestClient, setup: VoiceSetup, **choices: Any) -> dict[str, Any]:
    response = client.put(
        path(setup), json={**SWITCHES, **choices}, headers=bearer("owner")
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def save_staff_number(setup: VoiceSetup, number: str) -> None:
    setup.testbed.profile_repo.save(
        BusinessProfileDocument(
            business_id=setup.business.id,
            niche_key=NicheKey.ENTERTAINMENT,
            answers_language=LanguageTag("ka"),
            contacts=BusinessContacts(handoff_phone_number=E164PhoneNumber(number)),
        )
    )


def test_recording_and_transfers_are_off_by_default(
    setup: VoiceSetup, client: TestClient
) -> None:
    body: dict[str, Any] = client.get(path(setup), headers=bearer("owner")).json()

    assert body["is_recording_enabled"] is False
    assert body["is_staff_transfer_confirmed"] is False
    assert body["staff_transfer_confirmed_at"] is None
    assert body["transfer_phone_number"] is None
    assert body["staff_transfer_confirmed_by"] is None


def test_the_owner_turns_recording_on_and_confirms_the_staff_notice(
    setup: VoiceSetup, client: TestClient
) -> None:
    body = put(
        client, setup, is_recording_enabled=True, is_staff_transfer_confirmed=True
    )

    stored = setup.testbed.call_settings_repo.get_by_business(setup.business.id)
    assert stored is not None
    assert stored.is_recording_enabled is True
    assert stored.is_staff_transfer_confirmed is True
    assert stored.staff_transfer_confirmed_by == setup.business.members[0].user_id
    assert stored.staff_transfer_confirmed_at == setup.testbed.clock.now_microseconds()
    assert body["staff_transfer_confirmed_at"] == stored.staff_transfer_confirmed_at
    assert body["staff_transfer_confirmed_by"] == str(
        stored.staff_transfer_confirmed_by
    )


def test_a_request_without_them_leaves_them_and_a_withdrawal_forgets_who(
    setup: VoiceSetup, client: TestClient
) -> None:
    put(client, setup, is_recording_enabled=True, is_staff_transfer_confirmed=True)

    kept = put(client, setup)
    withdrawn = put(client, setup, is_staff_transfer_confirmed=False)

    assert kept["is_recording_enabled"] is True
    assert kept["is_staff_transfer_confirmed"] is True
    assert withdrawn["is_recording_enabled"] is True
    assert withdrawn["is_staff_transfer_confirmed"] is False
    stored = setup.testbed.call_settings_repo.get_by_business(setup.business.id)
    assert stored is not None
    assert stored.staff_transfer_confirmed_by is None
    assert stored.staff_transfer_confirmed_at is None


@pytest.mark.parametrize(
    ("number", "shown"),
    [("+995599777888", "+995599777888"), ("+39899123456", None)],
)
def test_the_staff_number_shown_is_one_calls_may_go_to(
    setup: VoiceSetup, client: TestClient, number: str, shown: str | None
) -> None:
    save_staff_number(setup, number)

    body: dict[str, Any] = client.get(path(setup), headers=bearer("owner")).json()

    assert body["transfer_phone_number"] == shown
