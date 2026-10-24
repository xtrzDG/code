"""
The demo restaurant's Channels page has a health line to show: each
channel's last customer message and reply come from the demo month, and
WhatsApp keeps a staff template in every language its guests write in.
"""

from typing import Any

from tests.demo.test_demo_seeding import (
    DEMO_ENVIRONMENT,
    RESTAURANT,
    businesses_by_name,
    sign_in_owner,
)
from tests.e2e.harness import start_workshop

type JsonObject = dict[str, Any]


def test_demo_channels_carry_their_last_messages_and_staff_templates() -> None:
    workshop = start_workshop(DEMO_ENVIRONMENT)
    with workshop.client as client:
        headers = sign_in_owner(workshop)
        restaurant = businesses_by_name(client, headers)[RESTAURANT]
        channels: list[JsonObject] = client.get(
            f"/v1/businesses/{restaurant['id']}/channels", headers=headers
        ).json()

    by_kind = {channel["channel"]: channel for channel in channels}
    for kind in ("telegram", "whatsapp", "web_chat"):
        assert by_kind[kind]["last_inbound_at"] is not None, kind
        assert by_kind[kind]["last_outbound_at"] is not None, kind
        assert by_kind[kind]["last_error_reason"] is None, kind
    whatsapp = by_kind["whatsapp"]
    assert [entry["language_code"] for entry in whatsapp["staff_reply_templates"]] == [
        "ka",
        "ru",
        "en",
        "he",
        "ar",
    ]
    assert whatsapp["staff_reply_template"] == {
        "name": "staff_reply",
        "language_code": "ka",
    }
