"""
The WHATSAPP_QUALITY alert (VOICE-09): Meta's warnings about a business's
WhatsApp number or templates, counted by the WhatsApp webhook and read by
the platform alerts job; the log line names the business account, never a
customer.
"""

import pytest

from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.adapters.channels.whatsapp_quality_signals import report_quality_warnings
from app.schemas.constants.monitoring import PlatformAlertCode, PlatformSignal
from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload
from app.utilities.channels.json_values import JsonObject
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.testbed import ChannelsTestbed
from tests.platform_ops.abuse_world import BookingWorld, quality_change
from tests.platform_ops.ops_documents import MINUTE

ACCOUNT_ID: str = "102290129340398"
ENTRY: JsonObject = {"id": ACCOUNT_ID}


@pytest.fixture
def world() -> BookingWorld:
    return BookingWorld()


@pytest.mark.parametrize(
    "change",
    [
        quality_change("phone_number_quality_update", event="FLAGGED"),
        quality_change("phone_number_quality_update", event="DOWNGRADE"),
        quality_change(
            "message_template_quality_update",
            new_quality_score="RED",
            message_template_name="reminder",
            message_template_language="it",
        ),
        quality_change(
            "message_template_status_update",
            event="PAUSED",
            message_template_name="reminder",
        ),
        quality_change(
            "template_category_update",
            new_category="MARKETING",
            message_template_name="text_back",
        ),
    ],
)
def test_meta_warnings_fire_the_whatsapp_quality_alert(
    world: BookingWorld, change: JsonObject, caplog: pytest.LogCaptureFixture
) -> None:
    report_quality_warnings(ENTRY, change, world.ops.signals)

    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 1
    assert world.observe(PlatformAlertCode.WHATSAPP_QUALITY).is_firing
    # The platform team finds the business by its WhatsApp Business Account.
    assert f"WhatsApp quality warning of business account {ACCOUNT_ID}" in caplog.text


@pytest.mark.parametrize(
    "change",
    [
        quality_change("phone_number_quality_update", event="UPGRADE"),
        quality_change("message_template_quality_update", new_quality_score="GREEN"),
        quality_change("message_template_status_update", event="APPROVED"),
        quality_change("template_category_update", new_category="UTILITY"),
        quality_change("account_update", event="VERIFIED_ACCOUNT"),
    ],
)
def test_good_news_from_meta_stays_quiet(
    world: BookingWorld, change: JsonObject
) -> None:
    report_quality_warnings(ENTRY, change, world.ops.signals)
    world.ops.clock.advance(MINUTE)

    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 0
    assert not world.observe(PlatformAlertCode.WHATSAPP_QUALITY).is_firing


@pytest.mark.parametrize("account", ["", "102290\n129340398", "x" * 20, "9" * 40])
def test_an_account_id_that_is_none_is_not_logged_as_one(
    world: BookingWorld, account: str, caplog: pytest.LogCaptureFixture
) -> None:
    report_quality_warnings(
        {"id": account},
        quality_change("phone_number_quality_update", event="FLAGGED"),
        world.ops.signals,
    )

    assert "WhatsApp quality warning of business account unknown" in caplog.text
    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 1


def test_the_whatsapp_webhook_counts_meta_s_warnings(
    world: BookingWorld, caplog: pytest.LogCaptureFixture
) -> None:
    testbed = ChannelsTestbed()
    adapter = WhatsAppChannelAdapter(
        testbed.meta_client,
        testbed.phone_number_parser,
        testbed.settings,
        signal_counter=world.ops.signals,
    )
    body = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": ACCOUNT_ID,
                "changes": [
                    quality_change("phone_number_quality_update", event="FLAGGED"),
                    quality_change(
                        "message_template_quality_update",
                        new_quality_score="YELLOW",
                        message_template_name="text_back",
                    ),
                ],
            }
        ],
    }

    messages = adapter.parse_webhook(ChannelWebhookPayload(body=to_json_bytes(body)))

    assert messages == []
    assert world.signals(PlatformSignal.WHATSAPP_QUALITY_DROP) == 2
    assert f"business account {ACCOUNT_ID}" in caplog.text
