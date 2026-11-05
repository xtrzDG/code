"""The Instagram card's comment-to-DM settings."""

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from tests.meta_connection.meta_world import MetaWorld

ON: dict[str, object] = {
    "is_on": True,
    "keywords": ["menu", "Menu", "price list"],
    "reply_text": "Hi! Here is our menu.",
}


def with_instagram(status: ChannelStatus = ChannelStatus.CONNECTED) -> MetaWorld:
    world = MetaWorld()
    world.testbed.add_channel(
        world.business.id,
        ChannelKind.INSTAGRAM,
        external_id="17841400000000001",
        secret="test-page-token-0000-0000",
        status=status,
    )
    return world


class TestCommentReplySettings:
    def test_the_owner_turns_them_on_with_distinct_keywords(self) -> None:
        world = with_instagram()

        response = world.set_comment_replies(ON)

        assert response.status_code == 200, response.text
        assert response.json()["comment_replies"] == {
            "is_on": True,
            # This release keeps the settings; the next one answers comments.
            "is_available": False,
            "keywords": ["menu", "price list"],
            "reply_text": "Hi! Here is our menu.",
        }
        stored = world.stored(ChannelKind.INSTAGRAM).comment_replies
        assert stored is not None and stored.is_on
        assert world.testbed.audit_actions(world.business.id) == [("update", "channel")]

    def test_off_keeps_the_keywords_and_text(self) -> None:
        world = with_instagram()
        world.set_comment_replies(ON)

        response = world.set_comment_replies(
            {"is_on": False, "keywords": ["menu"], "reply_text": "Later"}
        )

        assert response.json()["comment_replies"] == {
            "is_on": False,
            "is_available": False,
            "keywords": ["menu"],
            "reply_text": "Later",
        }

    @pytest.mark.usefixtures("next_release")
    def test_the_next_release_says_comments_are_answered(self) -> None:
        response = with_instagram().set_comment_replies(ON)

        assert response.json()["comment_replies"]["is_available"] is True

    def test_on_needs_a_keyword_and_a_reply(self) -> None:
        world = with_instagram()

        response = world.set_comment_replies({"is_on": True, "keywords": []})

        assert response.status_code == 422
        assert [reason["code"] for reason in response.json()["reasons"]] == [
            "comment_keywords_missing",
            "comment_reply_missing",
        ]

    def test_malformed_keywords_and_texts_are_refused(self) -> None:
        world = with_instagram()

        blank_edge = world.set_comment_replies(
            {"is_on": True, "keywords": [" menu"], "reply_text": "Hi"}
        )
        too_long = world.set_comment_replies(
            {"is_on": True, "keywords": ["menu"], "reply_text": "x" * 1001}
        )
        too_many = world.set_comment_replies(
            {
                "is_on": True,
                "keywords": [f"word{number}" for number in range(21)],
                "reply_text": "Hi",
            }
        )

        assert {
            blank_edge.status_code,
            too_long.status_code,
            too_many.status_code,
        } == {422}

    def test_only_the_owner_of_a_connected_instagram(self) -> None:
        connected = with_instagram()
        disconnected = with_instagram(ChannelStatus.DISABLED)

        staff = connected.set_comment_replies(ON, user="staff")
        stranger = connected.set_comment_replies(ON, user="stranger")
        off_channel = disconnected.set_comment_replies(ON)
        no_channel = MetaWorld().set_comment_replies(ON)

        assert staff.status_code == 403
        assert stranger.status_code == 404
        assert off_channel.status_code == 404
        assert no_channel.status_code == 404
