"""
The owner's controls of the assistant (AI-10): a pause and actions switched
off, saved with the settings only when sent, audited, and held by the
spend guard (the pause) and the tool runner (the switches).
"""

from typing import Any

import pytest

from tests.brain.test_assistant_settings_routes import SettingsScene
from tests.channels.channels_payloads import bearer


@pytest.fixture
def scene() -> SettingsScene:
    return SettingsScene()


def test_the_owner_pauses_the_assistant_and_switches_tools_off(
    scene: SettingsScene,
) -> None:
    response = scene.client.put(
        scene.path,
        json={
            "remembers_customers": True,
            "shares_team_notes": False,
            "is_paused": True,
            "disabled_tools": ["send_payment_link", "create_booking"],
        },
        headers=bearer("owner"),
    )

    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert body["is_paused"] is True
    assert body["disabled_tools"] == ["create_booking", "send_payment_link"]
    assert scene.testbed.audit_actions(scene.business.id)[-1] == (
        "update",
        "assistant_settings",
    )


def test_a_memory_change_leaves_the_controls_as_they_are(
    scene: SettingsScene,
) -> None:
    scene.client.put(
        scene.path,
        json={"is_paused": True, "disabled_tools": ["cancel_booking"]},
        headers=bearer("owner"),
    )

    response = scene.client.put(
        scene.path,
        json={"remembers_customers": False, "shares_team_notes": False},
        headers=bearer("owner"),
    )

    body: dict[str, Any] = response.json()
    assert body["remembers_customers"] is False
    assert body["is_paused"] is True
    assert body["disabled_tools"] == ["cancel_booking"]


def test_the_ways_out_cannot_be_switched_off(scene: SettingsScene) -> None:
    response = scene.client.put(
        scene.path,
        json={"disabled_tools": ["handoff_to_human"]},
        headers=bearer("owner"),
    )

    assert response.status_code == 422
    assert "handoff_to_human" in response.text
    assert scene.settings_repo.get_by_business(scene.business.id) is None


def test_staff_cannot_pause_the_assistant(scene: SettingsScene) -> None:
    response = scene.client.put(
        scene.path, json={"is_paused": True}, headers=bearer("staff")
    )

    assert response.status_code == 403
