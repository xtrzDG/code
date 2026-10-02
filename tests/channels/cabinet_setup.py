"""An owner, a staff member and their business behind the channel settings routes."""

from typing import Any

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.utilities.channels.delivery_targets import find_business_channel
from tests.channels.channels_payloads import HttpResponse, bearer, telegram_ok
from tests.channels.testbed import ChannelsTestbed

PAGE_ID: str = "4410001"

INSTAGRAM_ID: str = "17841400000000001"

PHONE_NUMBER_ID: str = "106540352242922"


class CabinetSetup:
    def __init__(self, settings: Any = None) -> None:
        self.testbed = ChannelsTestbed(settings)
        self.owner_id = self.testbed.add_user("owner")
        self.staff_id = self.testbed.add_user("staff")
        self.testbed.add_user("stranger")
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner_id, staff_ids=[self.staff_id]
        )
        self.client = self.testbed.build_http_client()

    def put(
        self, channel: str, body: dict[str, Any], token: str = "owner"
    ) -> HttpResponse:
        return self.client.put(
            f"/v1/businesses/{self.business.id}/channels/{channel}",
            json=body,
            headers=bearer(token),
        )

    def delete(self, channel: str, token: str = "owner") -> HttpResponse:
        return self.client.delete(
            f"/v1/businesses/{self.business.id}/channels/{channel}",
            headers=bearer(token),
        )

    def stored(self, kind: ChannelKind) -> ChannelDocument:
        channel = find_business_channel(
            self.testbed.channel_repo, self.business.id, kind
        )
        assert channel is not None
        return channel

    def script_telegram(self, username: str = "funicular_vr_bot") -> None:
        transport = self.testbed.telegram_transport
        transport.respond("POST", r"/getMe$", telegram_ok({"username": username}))
        transport.respond("POST", r"/setWebhook$", telegram_ok())
        transport.respond("POST", r"/deleteWebhook$", telegram_ok())

    def script_page(self, with_instagram: bool = True) -> None:
        page: dict[str, Any] = {"id": PAGE_ID, "name": "Funicular VR"}
        if with_instagram:
            page["instagram_business_account"] = {"id": INSTAGRAM_ID}
        self.testbed.meta_transport.respond("GET", rf"/{PAGE_ID}$", page)
        self.testbed.meta_transport.respond(
            "POST", rf"/{PAGE_ID}/subscribed_apps$", {"success": True}
        )
