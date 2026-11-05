"""Per-language WhatsApp templates for staff replies on the Channels page."""

import pytest

from app.schemas.constants.channels import ChannelKind
from tests.channels.cabinet_setup import PHONE_NUMBER_ID
from tests.channels.channel_setup_world import ChannelSetupWorld
from tests.channels.channels_payloads import bearer

GEORGIAN = {"name": "staff_reply", "language_code": "ka"}
HEBREW = {"name": "staff_reply_he", "language_code": "he"}
ARABIC = {"name": "staff_reply", "language_code": "ar"}


def with_whatsapp() -> ChannelSetupWorld:
    world = ChannelSetupWorld()
    world.testbed.add_channel(world.business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
    return world


def test_the_owner_keeps_one_template_per_language() -> None:
    world = with_whatsapp()

    saved = world.put_templates([HEBREW, GEORGIAN, ARABIC])
    listed = world.client.get(
        f"/v1/businesses/{world.business.id}/channels", headers=bearer("staff")
    )

    assert saved.status_code == 200, saved.text
    assert saved.json()["staff_reply_templates"] == [HEBREW, GEORGIAN, ARABIC]
    # The single template earlier clients and the previous release read: the
    # one of the business's default language.
    assert str(world.business.default_language) == "ka"
    assert saved.json()["staff_reply_template"] == GEORGIAN
    assert listed.json()[0]["staff_reply_templates"] == [HEBREW, GEORGIAN, ARABIC]
    stored = world.stored(ChannelKind.WHATSAPP)
    assert [str(entry.language_code) for entry in stored.whatsapp_staff_templates] == [
        "he",
        "ka",
        "ar",
    ]
    assert world.testbed.audit_actions(world.business.id)[-1] == ("update", "channel")


def test_an_empty_list_removes_every_template() -> None:
    world = with_whatsapp()
    world.put_templates([GEORGIAN, HEBREW])

    removed = world.put_templates([])

    assert removed.status_code == 200
    assert removed.json()["staff_reply_templates"] == []
    assert removed.json()["staff_reply_template"] is None
    stored = world.stored(ChannelKind.WHATSAPP)
    assert (stored.whatsapp_staff_templates, stored.whatsapp_staff_template) == (
        [],
        None,
    )


def test_two_templates_of_one_language_are_refused() -> None:
    world = with_whatsapp()

    refused = world.put_templates(
        [GEORGIAN, {"name": "other", "language_code": "ka"}, HEBREW, HEBREW]
    )

    assert refused.status_code == 422
    [reason] = refused.json()["reasons"]
    assert reason["code"] == "duplicate_template_language"
    assert reason["details"] == ["ka", "he"]
    assert world.stored(ChannelKind.WHATSAPP).whatsapp_staff_templates == []


@pytest.mark.parametrize(
    "entry",
    [
        {"name": "Staff Reply", "language_code": "ka"},
        {"name": "staff_reply", "language_code": "georgian"},
        {"name": "staff_reply"},
    ],
)
def test_malformed_templates_are_refused(entry: dict[str, str]) -> None:
    world = with_whatsapp()

    assert world.put_templates([entry]).status_code == 422


def test_only_owners_of_a_business_with_whatsapp_set_them() -> None:
    world = ChannelSetupWorld()

    without_whatsapp = world.put_templates([GEORGIAN])
    world.testbed.add_channel(world.business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
    by_staff = world.put_templates([GEORGIAN], user="staff")
    by_stranger = world.put_templates([GEORGIAN], user="stranger")

    assert without_whatsapp.status_code == 404
    assert by_staff.status_code == 403
    assert by_stranger.status_code == 404
    assert world.stored(ChannelKind.WHATSAPP).whatsapp_staff_templates == []


def test_the_single_template_route_replaces_the_list_with_its_template() -> None:
    world = with_whatsapp()
    world.put_templates([GEORGIAN, HEBREW])

    single = world.client.put(
        f"/v1/businesses/{world.business.id}/channels/whatsapp/staff-template",
        json=ARABIC,
        headers=bearer("owner"),
    )

    assert single.status_code == 200, single.text
    assert single.json()["staff_reply_templates"] == [ARABIC]
    assert single.json()["staff_reply_template"] == ARABIC
