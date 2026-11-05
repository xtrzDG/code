"""Meta channels refused by the platform turn ERROR and heal."""

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.utilities.channels.channel_health import summarize_channel_error
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN
from tests.channels.meta_payloads import PAGE_ID, page_message, page_webhook, post_meta
from tests.channels.stored_channels import stored
from tests.channels.testbed import ChannelsTestbed


class TestMetaChannelHealth:
    def test_expired_page_token_puts_messenger_in_error(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond(
            "POST",
            r"/me/messages$",
            {
                "error": {
                    "message": "Error validating access token: Session has expired.",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
            status_code=400,
        )

        post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID)]),
        )
        testbed.run_worker()

        broken = stored(testbed, channel)
        assert broken.status is ChannelStatus.ERROR
        assert "(190)" in str(broken.last_error)
        assert "Session has expired" in str(broken.last_error)
        assert PAGE_ACCESS_TOKEN not in str(broken.last_error)

        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})
        post_meta(
            testbed,
            page_webhook(
                "page", PAGE_ID, [page_message("ps-1", "Again", PAGE_ID, mid="m2")]
            ),
        )
        testbed.run_worker()
        assert stored(testbed, channel).status is ChannelStatus.CONNECTED

    def test_temporary_meta_failures_leave_the_channel_connected(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond(
            "POST",
            r"/me/messages$",
            {"error": {"message": "Please retry", "code": 2}},
            status_code=500,
        )

        post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID)]),
        )
        testbed.run_worker()

        assert stored(testbed, channel).status is ChannelStatus.CONNECTED


def test_error_summaries_are_one_short_line() -> None:
    summary = summarize_channel_error("Line one\n  line two " + "x" * 400)

    assert "\n" not in str(summary)
    assert len(str(summary)) == 300
    assert str(summary).startswith("Line one line two x")
    assert str(summary).endswith("…")
    assert summarize_channel_error("   ") == (
        "The platform refused the channel's credential."
    )
