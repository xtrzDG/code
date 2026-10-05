"""
Settings → General's customer memory over HTTP: the team reads the switch,
owners change it (audited), strangers never see the business.
"""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.gateways.http.assistant_settings_routes import (
    build_assistant_settings_router,
)
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.repositories.assistant_settings_repository import (
    AssistantSettingsRepository,
)
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.businesses import BusinessDocument
from app.use_cases.conversations.memory.get_assistant_settings_use_case import (
    GetAssistantSettingsUseCase,
)
from app.use_cases.conversations.memory.update_assistant_settings_use_case import (
    UpdateAssistantSettingsUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.channels.channels_http import wrap_use_case
from tests.channels.channels_payloads import bearer
from tests.channels.testbed import ChannelsTestbed


class SettingsScene:
    def __init__(self) -> None:
        self.testbed = ChannelsTestbed()
        owner_id = self.testbed.add_user("owner")
        staff_id = self.testbed.add_user("staff")
        self.testbed.add_user("stranger")
        self.business: BusinessDocument = self.testbed.add_business(
            owner_id, staff_ids=[staff_id]
        )
        self.settings_repo = AssistantSettingsRepository(
            InMemoryDocumentCollectionAdapter(AssistantSettingsDocument)
        )
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_assistant_settings_router(
                current_user=build_current_user_dependency(
                    self.testbed.authentication, SessionAssuranceContext()
                ),
                get_assistant_settings_operator=wrap_use_case(
                    GetAssistantSettingsUseCase(
                        authorize_business_access=self.testbed.authorize_business_access,
                        assistant_settings_repo=self.settings_repo,
                    )
                ),
                update_assistant_settings_operator=wrap_use_case(
                    UpdateAssistantSettingsUseCase(
                        authorize_business_access=self.testbed.authorize_business_access,
                        assistant_settings_repo=self.settings_repo,
                        audit_log_repo=self.testbed.audit_log_repo,
                        wall_clock=self.testbed.wall_clock,
                    )
                ),
            )
        )
        self.client = TestClient(application)

    @property
    def path(self) -> str:
        return f"/v1/businesses/{self.business.id}/assistant-settings"


@pytest.fixture
def scene() -> SettingsScene:
    return SettingsScene()


def test_the_defaults_remember_customers_without_the_team_notes(
    scene: SettingsScene,
) -> None:
    response = scene.client.get(scene.path, headers=bearer("staff"))

    assert response.status_code == 200, response.text
    assert response.json() == {
        "remembers_customers": True,
        "shares_team_notes": False,
        "updated_at": None,
    }


def test_the_owner_turns_the_memory_off_and_it_is_audited(
    scene: SettingsScene,
) -> None:
    response = scene.client.put(
        scene.path,
        json={"remembers_customers": False, "shares_team_notes": False},
        headers=bearer("owner"),
    )

    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    assert body["remembers_customers"] is False
    assert body["updated_at"] is not None
    stored = scene.settings_repo.get_by_business(scene.business.id)
    assert stored is not None and stored.remembers_customers is False
    assert scene.testbed.audit_actions(scene.business.id)[-1] == (
        "update",
        "assistant_settings",
    )
    again = scene.client.get(scene.path, headers=bearer("owner")).json()
    assert again["remembers_customers"] is False


def test_staff_cannot_change_the_settings(scene: SettingsScene) -> None:
    response = scene.client.put(
        scene.path, json={"shares_team_notes": True}, headers=bearer("staff")
    )

    assert response.status_code == 403
    assert scene.settings_repo.get_by_business(scene.business.id) is None


def test_a_stranger_does_not_find_the_business(scene: SettingsScene) -> None:
    assert scene.client.get(scene.path, headers=bearer("stranger")).status_code == 404
    response = scene.client.put(scene.path, json={}, headers=bearer("stranger"))
    assert response.status_code == 404


def test_unknown_fields_are_refused(scene: SettingsScene) -> None:
    response = scene.client.put(
        scene.path, json={"remembers_everything": True}, headers=bearer("owner")
    )

    assert response.status_code == 422
