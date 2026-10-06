"""
What each Meta fixture must become: the customer messages a channel
adapter reads from it, or the kinds it skips (and logs) instead.
"""

from dataclasses import dataclass
from typing import Any

from app.contracts.channels import ChannelAdapterContract
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from tests.channels.testbed import ChannelsTestbed

WHATSAPP_SPEC: str = "meta_whatsapp_cloud_api.json"
PAGES_SPEC: str = "meta_messenger_platform.json"
WHATSAPP_ACCOUNT: str = "106540352242922"
SHEENA: dict[str, Any] = {
    "channel": "whatsapp",
    "account": WHATSAPP_ACCOUNT,
    "customer": "16505551234",
    "name": "Sheena Nelson",
    "phone": "+16505551234",
    "attachments": [],
    "source": None,
}
MESSENGER: dict[str, Any] = {
    "channel": "messenger",
    "account": "104922111111111",
    "customer": "7034567890123456",
    "name": None,
    "phone": None,
    "attachments": [],
    "source": None,
}
INSTAGRAM: dict[str, Any] = {
    **MESSENGER,
    "channel": "instagram",
    "account": "17841405822304914",
    "customer": "1259384756103948",
}


@dataclass(frozen=True)
class MetaCase:
    """A fixture and the messages it gives, or the kinds it skips."""

    fixture: str
    messages: tuple[dict[str, Any], ...] = ()
    skipped: str | None = None


WHATSAPP_CASES: tuple[MetaCase, ...] = (
    MetaCase(
        "whatsapp_text.json",
        ({**SHEENA, "text": "Does it come in another color?"},),
    ),
    MetaCase(
        "whatsapp_text_from_ad.json",
        (
            {
                **SHEENA,
                "text": "Hello! Can I get more info on this?",
                "source": "ad-120226305854810726",
            },
        ),
    ),
    MetaCase("whatsapp_button.json", ({**SHEENA, "text": "Unsubscribe"},)),
    MetaCase("whatsapp_interactive_button_reply.json", ({**SHEENA, "text": "Cancel"},)),
    MetaCase(
        "whatsapp_interactive_list_reply.json",
        ({**SHEENA, "text": "Priority Mail Express"},),
    ),
    MetaCase(
        "whatsapp_image.json", ({**SHEENA, "text": "", "attachments": ["image"]},)
    ),
    MetaCase(
        "whatsapp_audio.json", ({**SHEENA, "text": "", "attachments": ["audio"]},)
    ),
    MetaCase(
        "whatsapp_location.json",
        ({**SHEENA, "text": "", "attachments": ["location"]},),
    ),
    MetaCase("whatsapp_reaction.json", skipped="message:reaction=1"),
    MetaCase("whatsapp_system.json", skipped="message:system=1"),
    MetaCase("whatsapp_status_delivered.json", skipped="status:delivered=1"),
    MetaCase("whatsapp_status_failed_131047.json", skipped="status:failed=1"),
    MetaCase("whatsapp_status_failed_131026.json", skipped="status:failed=1"),
    MetaCase("whatsapp_group_create.json", skipped="field:group_lifecycle_update=1"),
    MetaCase("whatsapp_unknown_field.json", skipped="field:other=1"),
)

PAGE_CASES: tuple[MetaCase, ...] = (
    MetaCase(
        "messenger_message.json",
        ({**MESSENGER, "text": "Hi! Do you have a table for four tonight?"},),
    ),
    MetaCase(
        "messenger_postback.json",
        ({**MESSENGER, "text": "Get Started", "source": "src_flyer"},),
    ),
    MetaCase("messenger_echo.json", skipped="echo=1"),
    MetaCase("messenger_read.json", skipped="read=1"),
    MetaCase("messenger_unknown_event.json", skipped="other=1"),
    MetaCase(
        "instagram_message.json", ({**INSTAGRAM, "text": "Сколько стоит стрижка?"},)
    ),
    MetaCase(
        "instagram_story_reply.json",
        ({**INSTAGRAM, "text": "Is this colour still available?"},),
    ),
    MetaCase("instagram_echo.json", skipped="echo=1"),
    MetaCase("instagram_read.json", skipped="read=1"),
)

# Fixtures whose kind of event the vendor's own specification does not
# list: the adapters must tolerate them although the spec would reject them.
OUTSIDE_THE_SPEC: frozenset[str] = frozenset({"whatsapp_unknown_field.json"})


def adapter_for(testbed: ChannelsTestbed, fixture: str) -> ChannelAdapterContract:
    adapters: dict[str, ChannelAdapterContract] = {
        "whatsapp": testbed.whatsapp_adapter,
        "messenger": testbed.messenger_adapter,
        "instagram": testbed.instagram_adapter,
    }
    return adapters[fixture.split("_", 1)[0]]


def summarize(message: ChannelInboundMessage) -> dict[str, Any]:
    """The normalized message without its provider id (checked separately)."""

    return {
        "channel": message.channel.value,
        "account": None if message.account_id is None else str(message.account_id),
        "customer": str(message.channel_user_id),
        "text": str(message.text),
        "name": None if message.contact_name is None else str(message.contact_name),
        "phone": (
            None
            if message.contact_phone_number is None
            else str(message.contact_phone_number)
        ),
        "attachments": [attachment.kind.value for attachment in message.attachments],
        "source": (
            None
            if message.acquisition_source is None
            else str(message.acquisition_source)
        ),
    }
