"""Settings → Calls: the owner's switches, the template texts, the latest text-backs."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.constants.calls import MissedCallReason, MissedCallSource
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessMember
from app.schemas.dto.calls.missed_calls import MissedCallReport
from app.schemas.typings.conversations.strings import ProviderCallId
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from tests.calls.call_steps import connect_whatsapp, save_call_settings
from tests.calls.calls_http import build_calls_http_client
from tests.channels.channels_payloads import bearer
from tests.channels.voice_setup import ASSISTANT_LINE, VoiceSetup, build_voice_setup


def settings_path(setup: VoiceSetup) -> str:
    return f"/v1/businesses/{setup.business.id}/call-settings"


def text_backs_path(setup: VoiceSetup) -> str:
    return f"/v1/businesses/{setup.business.id}/text-backs"


@pytest.fixture
def setup() -> VoiceSetup:
    voice_setup = build_voice_setup()
    staff_id = voice_setup.testbed.add_user("staff")
    voice_setup.business.members.append(
        BusinessMember(user_id=staff_id, role=BusinessMemberRole.STAFF)
    )
    voice_setup.testbed.business_repo.save(voice_setup.business)
    return voice_setup


@pytest.fixture
def client(setup: VoiceSetup) -> TestClient:
    return build_calls_http_client(setup.testbed)


class TestCallSettings:
    def test_the_defaults(self, setup: VoiceSetup, client: TestClient) -> None:
        response = client.get(settings_path(setup), headers=bearer("owner"))

        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        assert body["is_summary_enabled"] is True
        assert body["is_text_back_enabled"] is False
        assert body["text_back_template_name"] is None
        assert body["is_sms_fallback_enabled"] is True
        assert body["is_whatsapp_connected"] is False
        assert body["is_sms_available"] is True
        previews = {
            preview["language"]: preview for preview in body["template_previews"]
        }
        assert list(previews) == ["ka", "ru", "en"]
        assert "{{1}}" in previews["en"]["template_body"]
        assert "{business}" not in previews["en"]["template_body"]
        assert "Funicular VR" in previews["en"]["example"]
        assert "Funicular VR" in previews["ka"]["example"]

    def test_the_owner_changes_them(
        self, setup: VoiceSetup, client: TestClient
    ) -> None:
        connect_whatsapp(setup)

        response = client.put(
            settings_path(setup),
            json={
                "is_summary_enabled": False,
                "is_text_back_enabled": True,
                "text_back_template_name": "missed_call_text_back",
                "is_sms_fallback_enabled": False,
            },
            headers=bearer("owner"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["is_whatsapp_connected"] is True
        stored = setup.testbed.call_settings_repo.get_by_business(setup.business.id)
        assert stored is not None
        assert stored.is_summary_enabled is False
        assert stored.is_text_back_enabled is True
        assert str(stored.text_back_template_name) == "missed_call_text_back"
        assert stored.is_sms_fallback_enabled is False
        assert ("update", "call_settings") in setup.testbed.audit_actions(
            setup.business.id
        )
        again = client.get(settings_path(setup), headers=bearer("owner")).json()
        assert again["is_text_back_enabled"] is True

    def test_a_template_name_meta_would_refuse(
        self, setup: VoiceSetup, client: TestClient
    ) -> None:
        response = client.put(
            settings_path(setup),
            json={"is_text_back_enabled": True, "text_back_template_name": "Missed!"},
            headers=bearer("owner"),
        )

        assert response.status_code == 422
        assert (
            setup.testbed.call_settings_repo.get_by_business(setup.business.id) is None
        )

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "call-settings"),
            ("PUT", "call-settings"),
            ("GET", "text-backs"),
        ],
    )
    def test_staff_and_strangers_are_refused(
        self, setup: VoiceSetup, client: TestClient, method: str, path: str
    ) -> None:
        url = f"/v1/businesses/{setup.business.id}/{path}"
        body = {"is_text_back_enabled": True} if method == "PUT" else None

        as_staff = client.request(method, url, json=body, headers=bearer("staff"))
        anonymous = client.request(method, url, json=body)

        assert as_staff.status_code == 403
        assert anonymous.status_code == 401


class TestTextBackList:
    def test_the_latest_first_one_page_at_a_time(
        self, setup: VoiceSetup, client: TestClient
    ) -> None:
        save_call_settings(setup, template_name=None)
        for index, caller in enumerate(
            ["+995599000001", "+995599000002", "+995599000003"]
        ):
            setup.testbed.missed_calls.execute(
                MissedCallReport(
                    source=MissedCallSource.PBX,
                    provider_call_id=ProviderCallId(f"in_{index}"),
                    reason=MissedCallReason.BUSY,
                    called_at=setup.testbed.clock.now_microseconds(),
                    assistant_number=RawPhoneNumberInput(ASSISTANT_LINE),
                    caller_number=RawPhoneNumberInput(caller),
                )
            )
            setup.testbed.clock.advance(60)
        setup.testbed.run_worker()

        first = client.get(
            text_backs_path(setup), params={"limit": 2}, headers=bearer("owner")
        ).json()
        rest = client.get(
            text_backs_path(setup),
            params={"limit": 2, "cursor": first["next_cursor"]},
            headers=bearer("owner"),
        ).json()

        assert [item["caller_phone_number"] for item in first["items"]] == [
            "+995599000003",
            "+995599000002",
        ]
        assert [item["caller_phone_number"] for item in rest["items"]] == [
            "+995599000001"
        ]
        assert rest["next_cursor"] is None
        [latest, *_] = first["items"]
        assert latest["reason"] == "busy"
        assert latest["source"] == "pbx"
        assert latest["status"] == "sent"
        assert latest["channel"] == "sms"
        assert latest["language"] == "ka"
        [views] = [
            entry
            for entry in setup.testbed.audit_log_repo.list_by_business(
                setup.business.id
            )
            if (entry.action.value, str(entry.entity)) == ("view", "missed_call")
        ]
        assert views.record_count == 2

    def test_no_text_backs_yet(self, setup: VoiceSetup, client: TestClient) -> None:
        response = client.get(text_backs_path(setup), headers=bearer("owner"))

        assert response.json() == {"items": [], "next_cursor": None}
