"""
A caller id proves nobody's identity: a call never joins a contact a
channel proved, never makes or overwrites a verified phone, and its tools
get no verified phone. Calls from one number share a call-only contact.
"""

from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.conversations import VoiceToolCallRequest
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmToolInputJson,
    ProviderCallId,
)
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.use_cases.conversations.open_voice_conversation_use_case import (
    OpenVoiceConversationUseCase,
)
from tests.brain.brain_world import BrainWorld, build_world
from tests.brain.scripted_turns import scripted
from tests.brain.test_voice_tool_calls import AVAILABILITY_INPUT, voice_call

CALLER: str = "+995599123456"


def proved_whatsapp_customer(world: BrainWorld) -> ContactDocument:
    """Nino, whose phone WhatsApp proved, with the PHONE identity of a text-back."""

    contact = ContactDocument(
        business_id=world.business.id,
        name=ContactName("Nino"),
        phone_number=E164PhoneNumber(CALLER),
        verified_phone_number=E164PhoneNumber(CALLER),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId(CALLER.removeprefix("+")),
            ),
            ChannelIdentity(
                channel=ChannelKind.PHONE, channel_user_id=ChannelUserId(CALLER)
            ),
        ],
    )
    world.contact_repo.save(contact)
    return contact


def call_contact(world: BrainWorld, call_id: str) -> ContactDocument:
    [conversation] = [
        conversation
        for conversation in world.conversations()
        if conversation.channel_user_id == call_id
    ]
    contact = world.contact_repo.get(world.business.id, conversation.contact_id)
    assert contact is not None
    return contact


def test_a_call_from_a_proved_number_gets_a_contact_of_its_own() -> None:
    world = build_world(scripted())
    nino = proved_whatsapp_customer(world)

    voice_call(world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT)

    caller = call_contact(world, "el_call_1")
    assert caller.id != nino.id
    assert caller.phone_number == CALLER  # Staff can call it back.
    assert caller.verified_phone_number is None
    assert caller.name is None
    stored_nino = world.contact_repo.get(world.business.id, nino.id)
    assert stored_nino == nino


def test_calls_from_one_number_share_their_call_only_contact() -> None:
    world = build_world(scripted())

    voice_call(world, AssistantToolName.CHECK_AVAILABILITY, AVAILABILITY_INPUT)
    voice_call(
        world,
        AssistantToolName.CHECK_AVAILABILITY,
        AVAILABILITY_INPUT,
        call_id="el_call_2",
    )

    first = call_contact(world, "el_call_1")
    second = call_contact(world, "el_call_2")
    assert first.id == second.id
    assert first.verified_phone_number is None
    assert [str(identity.channel_user_id) for identity in first.channel_identities] == [
        CALLER
    ]


def test_the_tools_of_a_call_get_no_verified_phone() -> None:
    world = build_world(scripted())
    proved_whatsapp_customer(world)

    open_call = OpenVoiceConversationUseCase(
        business_repo=world.business_repo,
        assistant_version_repo=world.version_repo,
        contact_repo=world.contact_repo,
        conversation_repo=world.conversation_repo,
        channel_repo=world.channel_repo,
        plan_registry=PlanRegistry(),
        wall_clock=world.clock.wall_clock(),
    )

    context = open_call.run(
        VoiceToolCallRequest(
            business_id=world.business.id,
            provider_call_id=ProviderCallId("el_call_9"),
            caller_phone_number=E164PhoneNumber(CALLER),
            tool_name=AssistantToolName.CHECK_AVAILABILITY,
            input_json=LlmToolInputJson(AVAILABILITY_INPUT),
            language=LanguageTag("ka"),
        )
    )

    assert context.verified_phone_number is None
    assert context.contact_phone_number == CALLER
    assert context.contact_name is None
