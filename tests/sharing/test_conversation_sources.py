"""A conversation keeps where its customer came from, set once when it starts."""

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.sharing.constrained_strings import AcquisitionSourceTag
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import say, scripted


def send(
    world: BrainWorld,
    text: str,
    source: str | None,
    user_id: str = "995555123456",
) -> None:
    world.pipeline.start(
        InboundMessage(
            business_id=world.business.id,
            channel=ChannelKind.WHATSAPP,
            channel_user_id=ChannelUserId(user_id),
            text=MessageText(text),
            acquisition_source=(
                None if source is None else AcquisitionSourceTag(source)
            ),
        )
    )


def only_conversation(world: BrainWorld) -> ConversationDocument:
    [conversation] = world.conversations()
    return conversation


def test_a_new_conversation_keeps_the_source_of_its_first_message() -> None:
    world = build_world(scripted(say("Hello!"), say("Of course.")))

    send(world, "Hi! (#qr)", "qr")
    send(world, "A table for two?", None)

    assert only_conversation(world).acquisition_source == "qr"


def test_a_later_source_never_rewrites_an_open_conversation() -> None:
    world = build_world(scripted(say("Hello!"), say("Of course.")))

    send(world, "Hi!", None)
    send(world, "Hi again (#flyer)", "flyer")

    assert only_conversation(world).acquisition_source is None


def test_each_customer_has_their_own_source() -> None:
    world = build_world(scripted(say("Hello!"), say("Hello!")))

    send(world, "Hi", "qr", user_id="995555000001")
    send(world, "Hi", "instagram-bio", user_id="995555000002")

    assert sorted(
        str(conversation.acquisition_source) for conversation in world.conversations()
    ) == ["instagram-bio", "qr"]
