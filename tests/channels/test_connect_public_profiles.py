"""The public addresses share links open, learned when a channel connects."""

from app.schemas.constants.channels import ChannelKind
from tests.channels.cabinet_setup import (
    INSTAGRAM_ID,
    PAGE_ID,
    PHONE_NUMBER_ID,
    CabinetSetup,
)
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN

PAGE_BODY = {"page_id": PAGE_ID, "page_access_token": PAGE_ACCESS_TOKEN}


def test_the_whatsapp_number_is_kept_in_the_form_wa_me_links_use() -> None:
    setup = CabinetSetup()
    setup.testbed.meta_transport.respond(
        "GET",
        rf"/{PHONE_NUMBER_ID}$",
        {"id": PHONE_NUMBER_ID, "display_phone_number": "+995 32 200-00-00"},
    )

    assert (
        setup.put("whatsapp", {"phone_number_id": PHONE_NUMBER_ID}).status_code == 200
    )

    profile = setup.stored(ChannelKind.WHATSAPP).public_profile
    assert profile is not None
    assert profile.whatsapp_number == "995322000000"


def test_a_number_meta_does_not_show_leaves_the_link_for_later() -> None:
    setup = CabinetSetup()
    setup.testbed.meta_transport.respond(
        "GET", rf"/{PHONE_NUMBER_ID}$", {"id": PHONE_NUMBER_ID}
    )

    assert (
        setup.put("whatsapp", {"phone_number_id": PHONE_NUMBER_ID}).status_code == 200
    )

    profile = setup.stored(ChannelKind.WHATSAPP).public_profile
    assert profile is not None
    assert profile.whatsapp_number is None


def test_page_and_instagram_usernames_are_read_with_the_page() -> None:
    setup = CabinetSetup()
    setup.script_page()
    setup.testbed.meta_transport.respond(
        "GET",
        rf"/{PAGE_ID}$",
        {
            "id": PAGE_ID,
            "name": "Funicular VR",
            "username": "funicularvr",
            "instagram_business_account": {
                "id": INSTAGRAM_ID,
                "username": "funicular.vr",
            },
        },
    )

    assert setup.put("messenger", PAGE_BODY).status_code == 200
    assert setup.put("instagram", PAGE_BODY).status_code == 200

    messenger = setup.stored(ChannelKind.MESSENGER).public_profile
    instagram = setup.stored(ChannelKind.INSTAGRAM).public_profile
    assert messenger is not None
    assert messenger.page_username == "funicularvr"
    assert messenger.instagram_username is None
    assert instagram is not None
    assert instagram.instagram_username == "funicular.vr"
    page_request = setup.testbed.meta_transport.requests[0]
    assert "username" in page_request.url.params["fields"]


def test_malformed_usernames_are_left_out() -> None:
    setup = CabinetSetup()
    setup.script_page()
    setup.testbed.meta_transport.respond(
        "GET",
        rf"/{PAGE_ID}$",
        {
            "id": PAGE_ID,
            "username": "no",
            "instagram_business_account": {"id": INSTAGRAM_ID, "username": "bad name!"},
        },
    )

    assert setup.put("instagram", PAGE_BODY).status_code == 200

    profile = setup.stored(ChannelKind.INSTAGRAM).public_profile
    assert profile is not None
    assert profile.page_username is None
    assert profile.instagram_username is None
