"""Checking a @BotFather token before connecting: the bot, its name and photo."""

import base64

from tests.channels.channel_setup_world import (
    BOT_TOKEN,
    PHOTO_BYTES,
    ChannelSetupWorld,
)
from tests.channels.channels_payloads import telegram_ok

PHOTO_SIZES: list[list[dict[str, object]]] = [
    [
        {"file_id": "small", "width": 80, "height": 80},
        {"file_id": "photo-160", "width": 160, "height": 160},
        {"file_id": "photo-640", "width": 640, "height": 640},
    ]
]


def test_the_owner_sees_the_bot_a_token_opens_and_nothing_is_saved() -> None:
    world = ChannelSetupWorld()
    world.script_bot(PHOTO_SIZES)

    checked = world.check_token("  " + BOT_TOKEN + " ")

    assert checked.status_code == 200, checked.text
    body = checked.json()
    assert body["username"] == "mtsvane_ezo_bot"
    assert body["display_name"] == "Mtsvane Ezo"
    expected = base64.b64encode(PHOTO_BYTES).decode()
    assert body["avatar_data_url"] == f"data:image/jpeg;base64,{expected}"
    photo_lookup = world.telegram.requests_to("/getUserProfilePhotos")[0].json()
    assert photo_lookup == {"user_id": 7012345678, "limit": 1}
    # The 160 px size: the smallest that is at least 96 px wide.
    assert world.telegram.requests_to("/getFile")[0].json() == {"file_id": "photo-160"}
    # Nothing connected: no webhook, no channel, no token kept.
    assert world.telegram.requests_to("/setWebhook") == []
    assert world.testbed.channel_repo.list_by_business(world.business.id) == []
    assert BOT_TOKEN not in checked.text


def test_a_bot_without_a_photo_or_with_a_broken_one_is_still_shown() -> None:
    without = ChannelSetupWorld()
    without.script_bot([])
    broken = ChannelSetupWorld()
    broken.script_bot(PHOTO_SIZES, photo=b"<html>not an image</html>")
    unreachable = ChannelSetupWorld()
    unreachable.script_bot(PHOTO_SIZES)
    unreachable.telegram.respond(
        "POST", r"/getFile$", {"ok": False, "error_code": 400}, 400
    )

    for world in (without, broken, unreachable):
        checked = world.check_token()
        assert checked.status_code == 200, checked.text
        assert checked.json()["username"] == "mtsvane_ezo_bot"
        assert checked.json()["avatar_data_url"] is None


def test_a_token_of_the_wrong_shape_or_rejected_by_telegram_is_explained() -> None:
    world = ChannelSetupWorld()
    world.telegram.respond(
        "POST",
        r"/getMe$",
        {"ok": False, "error_code": 401, "description": "Unauthorized"},
        401,
    )

    malformed = world.check_token("not-a-token")
    rejected = world.check_token()

    assert malformed.status_code == 422
    assert [reason["code"] for reason in malformed.json()["reasons"]] == [
        "telegram_token_format"
    ]
    assert rejected.status_code == 422
    assert [reason["code"] for reason in rejected.json()["reasons"]] == [
        "telegram_token_rejected"
    ]
    assert world.telegram.requests_to("/getMe")[0].path.endswith("/getMe")


def test_telegram_down_is_a_provider_error_not_a_bad_token() -> None:
    world = ChannelSetupWorld()
    world.telegram.respond(
        "POST", r"/getMe$", {"ok": False, "error_code": 502, "description": "Bad"}, 502
    )

    checked = world.check_token()

    assert checked.status_code == 502
    assert checked.json()["error"] == "external_service_error"


def test_only_owners_check_tokens_and_a_business_checks_twenty_per_ten_minutes() -> (
    None
):
    world = ChannelSetupWorld()
    world.script_bot([])

    by_staff = world.check_token(user="staff")
    by_stranger = world.check_token(user="stranger")
    allowed = [world.check_token().status_code for _ in range(20)]
    limited = world.check_token()

    assert by_staff.status_code == 403
    assert by_stranger.status_code == 404
    assert set(allowed) == {200}
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


def test_a_getme_answer_without_an_id_or_name_still_names_the_bot() -> None:
    world = ChannelSetupWorld()
    world.telegram.respond(
        "POST", r"/getMe$", telegram_ok({"username": "plain_bot", "first_name": " "})
    )

    checked = world.check_token()

    assert checked.status_code == 200, checked.text
    assert checked.json() == {
        "username": "plain_bot",
        "display_name": None,
        "avatar_data_url": None,
    }
    assert world.telegram.requests_to("/getUserProfilePhotos") == []
