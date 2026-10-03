"""Connecting a channel customers write in is a product event."""

from app.schemas.constants.analytics import ProductEventName
from app.schemas.constants.channels import ChannelKind
from tests.channels.cabinet_setup import CabinetSetup


def test_connecting_the_web_chat_reports_the_channel_and_its_owner() -> None:
    setup = CabinetSetup()

    assert setup.put("web", {}).status_code == 200

    [connected] = setup.testbed.product_events.named(ProductEventName.CHANNEL_CONNECTED)
    assert connected.properties.channel is ChannelKind.WEB_CHAT
    assert connected.business_id == setup.business.id
    assert str(connected.user_id) == str(setup.owner_id)


def test_a_refused_connection_reports_nothing() -> None:
    setup = CabinetSetup()

    assert setup.put("phone", {"phone_number": "12345"}).status_code == 422
    assert setup.put("web", {}, token="staff").status_code == 403

    assert setup.testbed.product_events.events == []
