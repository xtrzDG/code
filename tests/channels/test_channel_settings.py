"""Connecting the phone line and the web widget, and who may change channels."""

from typing import Any

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.typings.localization.constrained_strings import CountryCode
from tests.channels.cabinet_setup import INSTAGRAM_ID, PHONE_NUMBER_ID, CabinetSetup
from tests.channels.channels_payloads import bearer
from tests.channels.channels_settings import (
    BRAZIL,
    PAGE_ACCESS_TOKEN,
    TELEGRAM_BOT_TOKEN,
    UNITED_STATES,
)


class TestConnectPhoneAndWeb:
    @pytest.mark.parametrize(
        ("country", "typed_number", "expected"),
        [
            (BRAZIL, "(11) 96123-4567", "+5511961234567"),
            (UNITED_STATES, "(202) 555-0123", "+12025550123"),
        ],
    )
    def test_assistant_line_in_the_business_country(
        self, country: Any, typed_number: str, expected: str
    ) -> None:
        setup = CabinetSetup()
        setup.business.country_code = CountryCode(country.country_code)
        setup.testbed.business_repo.save(setup.business)

        response = setup.put("phone", {"phone_number": typed_number})

        assert response.status_code == 200
        assert response.json()["account_id"] == expected

    def test_international_number_and_country_hint(self) -> None:
        setup = CabinetSetup()
        hinted = setup.put(
            "phone", {"phone_number": "0 32 200 00 00", "country_hint": "GE"}
        )
        assert hinted.json()["account_id"] == "+995322000000"

        conflict_setup = CabinetSetup()
        other_owner = conflict_setup.testbed.add_user("other")
        other = conflict_setup.testbed.add_business(other_owner, name="Other")
        conflict_setup.testbed.add_channel(other.id, ChannelKind.PHONE, "+995322000000")
        assert (
            conflict_setup.put(
                "phone", {"phone_number": "+995 32 200 00 00"}
            ).status_code
            == 409
        )
        assert conflict_setup.put("phone", {"phone_number": "12345"}).status_code == 422
        assert conflict_setup.put("phone", {}).status_code == 422

    def test_web_chat_by_its_short_name(self) -> None:
        setup = CabinetSetup()

        response = setup.put("web", {})

        assert response.status_code == 200
        assert response.json()["channel"] == "web_chat"
        assert setup.stored(ChannelKind.WEB_CHAT).status is ChannelStatus.CONNECTED
        assert setup.delete("web_chat").status_code == 204
        assert setup.stored(ChannelKind.WEB_CHAT).status is ChannelStatus.DISABLED


class TestChannelAccess:
    def test_only_owners_change_channels(self) -> None:
        setup = CabinetSetup()

        assert setup.put("web", {}, token="staff").status_code == 403
        assert setup.put("web", {}, token="stranger").status_code == 404
        assert setup.delete("web", token="staff").status_code == 403

    def test_unknown_and_unsupported_channels(self) -> None:
        setup = CabinetSetup()

        assert setup.put("fax", {}).status_code == 404
        assert setup.put("viber", {}).status_code == 422
        assert setup.put("owner_test", {}).status_code == 422
        assert setup.delete("telegram").status_code == 404

    def test_members_list_channels_without_secrets(self) -> None:
        setup = CabinetSetup()
        setup.testbed.add_channel(setup.business.id, ChannelKind.WEB_CHAT)
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.INSTAGRAM, INSTAGRAM_ID, PAGE_ACCESS_TOKEN
        )
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        other_owner = setup.testbed.add_user("other")
        other = setup.testbed.add_business(other_owner, name="Other")
        setup.testbed.add_channel(other.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)

        response = setup.client.get(
            f"/v1/businesses/{setup.business.id}/channels", headers=bearer("staff")
        )

        assert response.status_code == 200
        assert [item["channel"] for item in response.json()] == [
            "telegram",
            "instagram",
            "web_chat",
        ]
        assert PAGE_ACCESS_TOKEN not in response.text
        assert TELEGRAM_BOT_TOKEN not in response.text
        assert "encrypted_secret" not in response.text
        assert (
            setup.client.get(
                f"/v1/businesses/{setup.business.id}/channels",
                headers=bearer("stranger"),
            ).status_code
            == 404
        )
