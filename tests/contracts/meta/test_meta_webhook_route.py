"""
Every Meta fixture through the whole webhook route: signed with the app
secret, acknowledged with 200 (never a 500, whatever the kind), routed to
the business that owns the account, answered by the worker; every request
the platform then sends to Meta matches the vendor's specification with
every object closed (a field Meta does not define fails).
"""

from typing import Any

import pytest

from app.schemas.constants.channels import ChannelKind
from app.utilities.channels.channel_endpoints import META_SIGNATURE_HEADER
from tests.channels.channels_payloads import HttpResponse, sign_meta
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN
from tests.channels.meta_payloads import post_meta
from tests.channels.testbed import ChannelsTestbed
from tests.contracts.contract_files import load_json_fixture
from tests.contracts.meta.meta_cases import (
    PAGE_CASES,
    PAGES_SPEC,
    WHATSAPP_CASES,
    WHATSAPP_SPEC,
    MetaCase,
)
from tests.contracts.vendor_schemas import assert_inbound, assert_outbound

ALL_CASES: tuple[MetaCase, ...] = WHATSAPP_CASES + PAGE_CASES
CHANNEL_KINDS: dict[str, ChannelKind] = {
    "whatsapp": ChannelKind.WHATSAPP,
    "messenger": ChannelKind.MESSENGER,
    "instagram": ChannelKind.INSTAGRAM,
}
MALFORMED_BODIES: tuple[bytes, ...] = (
    b"not json",
    b"[]",
    b"{}",
    b'{"object": "whatsapp_business_account", "entry": "oops"}',
    b'{"object": "page", "entry": [{"id": 5, "messaging": [null, 7]}]}',
    b'{"object": "instagram", "entry": [{"messaging": [{"sender": {}}]}]}',
)


def connected_testbed(fixture: str, body: dict[str, Any]) -> ChannelsTestbed:
    """A business whose channel owns the fixture's account, Meta answering."""

    testbed = ChannelsTestbed()
    business = testbed.add_business(testbed.add_user("owner"))
    platform: str = fixture.split("_", 1)[0]
    entry: dict[str, Any] = body["entry"][0]
    account_id: str = (
        entry["changes"][0]["value"]["metadata"]["phone_number_id"]
        if platform == "whatsapp"
        else entry["id"]
    )
    testbed.add_channel(
        business.id,
        CHANNEL_KINDS[platform],
        account_id,
        None if platform == "whatsapp" else PAGE_ACCESS_TOKEN,
    )
    testbed.meta_transport.respond(
        "POST",
        r"/\d+/messages$",
        load_json_fixture("meta", "whatsapp_send_response.json"),
    )
    testbed.meta_transport.respond(
        "POST",
        r"/me/messages$",
        load_json_fixture("meta", "messenger_send_response.json"),
    )
    return testbed


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda case: case.fixture)
def test_every_kind_is_acknowledged_and_replies_match_the_spec(case: MetaCase) -> None:
    body: dict[str, Any] = load_json_fixture("meta", case.fixture)
    testbed = connected_testbed(case.fixture, body)

    response = post_meta(testbed, body)
    testbed.run_worker()

    assert response.status_code == 200
    assert response.json()["received"] == len(case.messages)
    sent = testbed.meta_transport.requests
    assert len(sent) == len(case.messages)
    for request in sent:
        if request.path.endswith("/me/messages"):
            assert_outbound(request.json(), PAGES_SPEC, "request:messages.send")
        else:
            assert_outbound(request.json(), WHATSAPP_SPEC, "request:messages.send")


@pytest.mark.parametrize("body", MALFORMED_BODIES)
def test_malformed_but_signed_deliveries_are_acknowledged(body: bytes) -> None:
    testbed = ChannelsTestbed()
    response = post_meta_bytes(testbed, body)

    assert response.status_code == 200
    assert response.json()["received"] == 0


def test_send_responses_match_the_vendor_specification() -> None:
    assert_inbound(
        load_json_fixture("meta", "whatsapp_send_response.json"),
        WHATSAPP_SPEC,
        "MessageResponsePayload",
    )
    assert_inbound(
        load_json_fixture("meta", "messenger_send_response.json"),
        PAGES_SPEC,
        "response:messages.send",
    )


def post_meta_bytes(testbed: ChannelsTestbed, body: bytes) -> HttpResponse:
    return testbed.build_http_client().post(
        "/v1/channels/meta/webhook",
        content=body,
        headers={META_SIGNATURE_HEADER: sign_meta(body)},
    )
