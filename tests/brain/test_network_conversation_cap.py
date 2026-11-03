"""
A client network starts at most so many new website conversations an hour
(ABUSE-03): past the cap a new conversation gets the limit notice instead
of a model call, and its next message is answered as usual.
"""

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.use_cases.conversations.turns.network_conversation_cap import (
    PER_BUSINESS_PER_HOUR,
)
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.engine_helpers import requests_of
from tests.brain.scripted_turns import say, scripted

OFFICE: ClientIpAddress = ClientIpAddress("2a01:4f8:1:2::17")
SAME_NETWORK: ClientIpAddress = ClientIpAddress("2a01:4f8:1:2::99")
OTHER_NETWORK: ClientIpAddress = ClientIpAddress("81.2.69.160")
LOCAL: ClientIpAddress = ClientIpAddress("127.0.0.1")


def visit(world: BrainWorld, session: str, address: ClientIpAddress, text: str) -> str:
    reply = world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.WEB_CHAT,
            channel_user_id=ChannelUserId(session),
            text=MessageText(text),
            client_ip_address=address,
        )
    )
    return "" if reply.text is None else str(reply.text)


def test_a_network_past_its_hourly_cap_gets_the_notice_not_the_model() -> None:
    cap: int = int(PER_BUSINESS_PER_HOUR)
    world = build_world(scripted(*(say("Ciao!") for _ in range(cap + 3))))

    for number in range(cap):
        address = OFFICE if number % 2 == 0 else SAME_NETWORK
        assert visit(world, f"session-{number}", address, "Ciao").endswith("Ciao!")
    over = visit(world, "session-over", OFFICE, "Ciao")
    other = visit(world, "session-other", OTHER_NETWORK, "Ciao")
    again = visit(world, "session-over", OFFICE, "Avete un tavolo?")

    assert not over.endswith("Ciao!")
    assert over != ""
    assert other.endswith("Ciao!")
    assert again.endswith("Ciao!")
    assert len(requests_of(world)) == cap + 2


def test_messages_without_a_public_address_are_not_counted() -> None:
    cap: int = int(PER_BUSINESS_PER_HOUR)
    world = build_world(scripted(*(say("Hi!") for _ in range(2 * cap + 2))))

    for number in range(cap + 1):
        world.send("Hello", user_id=f"99555512{number:04d}")
        assert visit(world, f"local-{number}", LOCAL, "Hello").endswith("Hi!")

    assert len(requests_of(world)) == 2 * cap + 2
