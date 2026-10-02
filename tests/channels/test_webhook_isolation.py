"""One bad message of a webhook delivery never loses the others."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventStatus
from tests.channels.meta_payloads import (
    PHONE_NUMBER_ID,
    post_meta,
    whatsapp_message,
    whatsapp_webhook,
)
from tests.channels.outbox_reads import inbox
from tests.channels.testbed import ChannelsTestbed


def test_an_unexpected_error_of_one_message_spares_the_others() -> None:
    testbed = ChannelsTestbed()
    owner = testbed.add_user("owner")
    business = testbed.add_business(owner)
    testbed.add_channel(business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
    testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})
    testbed.pipeline.crashing_texts = {"boom"}

    response = post_meta(
        testbed,
        whatsapp_webhook(
            [
                whatsapp_message("995599000001", "boom", message_id="wamid.A"),
                whatsapp_message("995599000002", "hello", message_id="wamid.B"),
            ]
        ),
    )
    testbed.run_worker()

    assert response.json()["queued"] == 2
    [sent] = testbed.meta_transport.requests
    assert sent.json()["text"]["body"] == "Reply: hello"
    statuses = {
        str(event.customer_message.text): event.status
        for event in inbox(testbed)
        if event.customer_message is not None
    }
    # The crashed message is kept for the job's next attempt, not dropped.
    assert statuses == {
        "boom": InboundEventStatus.PROCESSING,
        "hello": InboundEventStatus.ANSWERED,
    }
    [crashed] = [event for event in inbox(testbed) if event.last_error is not None]
    assert crashed.lease_until is None
    assert str(crashed.last_error) == "a bug in a tool"
