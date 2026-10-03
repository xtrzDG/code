"""Choosing the WhatsApp template used to message staff."""

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from tests.channels.cabinet_setup import PHONE_NUMBER_ID, CabinetSetup
from tests.channels.channels_payloads import bearer


class TestWhatsAppStaffTemplate:
    def template_url(self, setup: CabinetSetup) -> str:
        return f"/v1/businesses/{setup.business.id}/channels/whatsapp/staff-template"

    def test_owner_sets_and_removes_the_template_for_staff_replies(self) -> None:
        setup = CabinetSetup()
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID
        )

        saved = setup.client.put(
            self.template_url(setup),
            json={"name": "staff_reply", "language_code": "pt_BR"},
            headers=bearer("owner"),
        )
        listed = setup.client.get(
            f"/v1/businesses/{setup.business.id}/channels", headers=bearer("staff")
        )
        stored_template = setup.stored(ChannelKind.WHATSAPP).whatsapp_staff_template
        removed = setup.client.put(
            self.template_url(setup), json={}, headers=bearer("owner")
        )

        assert saved.status_code == 200, saved.text
        assert saved.json()["staff_reply_template"] == {
            "name": "staff_reply",
            "language_code": "pt_BR",
        }
        assert listed.json()[0]["staff_reply_template"]["name"] == "staff_reply"
        assert stored_template is not None
        assert str(stored_template.language_code) == "pt_BR"
        assert removed.status_code == 200
        assert removed.json()["staff_reply_template"] is None
        assert setup.stored(ChannelKind.WHATSAPP).whatsapp_staff_template is None
        assert setup.testbed.audit_actions(setup.business.id)[-2:] == [
            ("update", "channel"),
            ("update", "channel"),
        ]

    def test_reconnecting_and_disabling_keep_the_template(self) -> None:
        setup = CabinetSetup()
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID
        )
        setup.client.put(
            self.template_url(setup),
            json={"name": "staff_reply", "language_code": "en"},
            headers=bearer("owner"),
        )

        disabled = setup.delete("whatsapp")

        assert disabled.status_code == 204
        stored = setup.stored(ChannelKind.WHATSAPP)
        assert stored.status is ChannelStatus.DISABLED
        assert stored.whatsapp_staff_template is not None
        assert str(stored.whatsapp_staff_template.name) == "staff_reply"
        assert str(stored.whatsapp_staff_template.language_code) == "en"

    @pytest.mark.parametrize(
        "body",
        [
            {"name": "staff_reply"},
            {"language_code": "en"},
            {"name": "Staff Reply", "language_code": "en"},
            {"name": "staff_reply", "language_code": "english"},
        ],
    )
    def test_incomplete_or_malformed_templates_are_refused(
        self, body: dict[str, str]
    ) -> None:
        setup = CabinetSetup()
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID
        )

        response = setup.client.put(
            self.template_url(setup), json=body, headers=bearer("owner")
        )

        assert response.status_code == 422
        assert setup.stored(ChannelKind.WHATSAPP).whatsapp_staff_template is None

    def test_only_owners_of_a_business_with_whatsapp_set_it(self) -> None:
        setup = CabinetSetup()
        body = {"name": "staff_reply", "language_code": "en"}

        without_whatsapp = setup.client.put(
            self.template_url(setup), json=body, headers=bearer("owner")
        )
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID
        )
        by_staff = setup.client.put(
            self.template_url(setup), json=body, headers=bearer("staff")
        )
        by_stranger = setup.client.put(
            self.template_url(setup), json=body, headers=bearer("stranger")
        )

        assert without_whatsapp.status_code == 404
        assert by_staff.status_code == 403
        assert by_stranger.status_code == 404
        assert setup.stored(ChannelKind.WHATSAPP).whatsapp_staff_template is None
