"""On the phone a link is never read aloud: it is texted when a messenger can."""

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.typings.channels.strings import ChannelExternalId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import scripted
from tests.brain.test_voice_tool_calls import voice_call
from tests.brain.tool_runner_helpers import build_context, run_tool

CALLER: str = "+995599123456"


def connect_telegram(world: BrainWorld) -> None:
    world.channel_repo.save(
        ChannelDocument(
            business_id=world.business.id,
            kind=ChannelKind.TELEGRAM,
            external_id=ChannelExternalId("sakhli_bot"),
            status=ChannelStatus.CONNECTED,
        )
    )


def know_caller_on_telegram(world: BrainWorld) -> None:
    world.contact_repo.save(
        ContactDocument(
            business_id=world.business.id,
            verified_phone_number=E164PhoneNumber(CALLER),
            channel_identities=[
                ChannelIdentity(
                    channel=ChannelKind.TELEGRAM,
                    channel_user_id=ChannelUserId("555000111"),
                )
            ],
        )
    )


def test_a_caller_reachable_on_a_messenger_is_promised_a_text() -> None:
    world = build_world(scripted())
    connect_telegram(world)
    know_caller_on_telegram(world)

    result, is_error = voice_call(
        world, AssistantToolName.SEND_LINK, '{"kind":"menu"}', caller=CALLER
    )

    assert is_error is False
    assert result["kind"] == "menu"
    assert result["texted_after_call"] is True
    assert "url" not in result
    assert "I will text you the link" in str(result["note"])


def test_a_caller_no_messenger_reaches_is_never_promised_a_text() -> None:
    world = build_world(scripted())
    # Known on Telegram, but the business has no Telegram connected.
    know_caller_on_telegram(world)

    result, _ = voice_call(
        world, AssistantToolName.SEND_LINK, '{"kind":"menu"}', caller=CALLER
    )

    assert result["texted_after_call"] is False
    assert "url" not in result
    assert "do not promise one" in str(result["note"])


def test_a_link_the_business_does_not_have_is_never_made_up() -> None:
    world = build_world(scripted())
    connect_telegram(world)
    know_caller_on_telegram(world)

    result, _ = voice_call(
        world, AssistantToolName.SEND_LINK, '{"kind":"payment"}', caller=CALLER
    )

    assert result == {
        "kind": "payment",
        "url": None,
        "note": "The business has no such link: do not invent one.",
    }


def test_in_chat_the_link_itself_is_sent() -> None:
    world = build_world(scripted())

    result, _ = run_tool(
        world,
        AssistantToolName.SEND_LINK,
        {"kind": "menu"},
        build_context(world, can_text_caller=True),
    )

    assert result == {"kind": "menu", "url": "https://sakhli.example/menu"}
