"""The widget's messages are limited per visitor and per client address."""

from typing import Any

from tests.channels.outbox_reads import inbox
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed


def post_message(
    client: Any, business_id: object, session_key: str = SESSION_KEY
) -> Any:
    return client.post(
        f"/v1/widget/{business_id}/messages",
        json={"session_key": session_key, "text": "Hi"},
    )


class TestWidgetMessageRateLimits:
    def test_a_visitor_sending_too_fast_waits_for_the_retry_after(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()

        answers: list[int] = []
        for _ in range(12):
            answers.append(post_message(client, business.id).status_code)
            testbed.clock.advance(5)
        testbed.clock.advance(-5)
        limited = post_message(client, business.id)
        other_visitor = post_message(client, business.id, "v1_another_visitor_77")

        assert answers == [202] * 12
        assert limited.status_code == 429
        assert limited.json()["error"] == "rate_limited"
        # The minute's 12 messages count fully until it ends in 5 s, then
        # fade with the next minute: 5 s into it there is room for one.
        assert limited.headers["Retry-After"] == "10"
        assert other_visitor.status_code == 202
        assert len(inbox(testbed)) == 13
        testbed.clock.advance(5)
        assert post_message(client, business.id).status_code == 429
        testbed.clock.advance(5)
        assert post_message(client, business.id).status_code == 202

    def test_one_address_is_limited_across_visitors(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()

        answers = [
            post_message(
                client, business.id, f"v1_visitor_number_{index:04d}"
            ).status_code
            for index in range(60)
        ]
        limited = post_message(client, business.id, "v1_one_more_visitor_0001")

        assert answers == [202] * 60
        assert limited.status_code == 429
        # The next minute starts in 60 s; a second into it, this minute's
        # weight leaves room for one more.
        assert limited.headers["Retry-After"] == "61"
        assert len(inbox(testbed)) == 60
