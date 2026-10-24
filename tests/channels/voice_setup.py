"""A business with a connected phone assistant line for the voice webhook tests."""

from dataclasses import dataclass
from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.assistants.constrained_integers import AssistantVersionNumber
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText, VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.webhook_signatures import derive_voice_tool_secret
from tests.channels.channels_settings import (
    ELEVENLABS_WEBHOOK_SECRET,
    GEORGIA,
    CountrySetup,
)
from tests.channels.testbed import ChannelsTestbed

ASSISTANT_LINE: str = "+995322000000"


CALLER: str = "+995599123456"


def tool_secret(business_id: BusinessId) -> str:
    return str(
        derive_voice_tool_secret(PlatformSecret(ELEVENLABS_WEBHOOK_SECRET), business_id)
    )


@dataclass
class VoiceSetup:
    testbed: ChannelsTestbed
    business: BusinessDocument
    contact: ContactDocument
    conversation: ConversationDocument


def build_voice_setup(
    country: CountrySetup = GEORGIA,
    settings: Any = None,
    conversation_language: str | None = "ka",
) -> VoiceSetup:
    testbed = ChannelsTestbed(settings)
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id, country=country)
    testbed.add_channel(business.id, ChannelKind.PHONE, ASSISTANT_LINE)
    version = AssistantVersionDocument(
        business_id=business.id,
        version_number=AssistantVersionNumber(1),
        niche_key=NicheKey.ENTERTAINMENT,
        model_id=LlmModelId("gpt-5-mini"),
        prompt_text=SystemPromptText("Prompt"),
        tools=[AssistantToolName.CREATE_BOOKING],
        languages=business.languages,
        default_language=business.default_language,
        is_voice_enabled=True,
        facts=[],
        profile_revision=Microseconds(1),
        voice_agent_id=VoiceAgentId("agent_1"),
    )
    testbed.assistant_version_repo.save(version)
    # A live business whose published version answers the phone.
    business.status = BusinessStatus.LIVE
    business.published_assistant_version_id = version.id
    testbed.business_repo.save(business)
    contact = ContactDocument(
        business_id=business.id,
        phone_number=E164PhoneNumber(CALLER),
        channel_identities=[
            ChannelIdentity(
                channel=ChannelKind.PHONE, channel_user_id=ChannelUserId(CALLER)
            ),
            ChannelIdentity(
                channel=ChannelKind.TELEGRAM, channel_user_id=ChannelUserId("555000111")
            ),
            ChannelIdentity(
                channel=ChannelKind.WHATSAPP,
                channel_user_id=ChannelUserId("995599123456"),
            ),
        ],
    )
    testbed.contact_repo.save(contact)
    conversation = ConversationDocument(
        business_id=business.id,
        contact_id=contact.id,
        assistant_version_id=version.id,
        channel=ChannelKind.PHONE,
        channel_user_id=ChannelUserId("conv_1"),
        language=None
        if conversation_language is None
        else LanguageTag(conversation_language),
        last_message_at=testbed.clock.now_microseconds(),
    )
    testbed.conversation_repo.save(conversation)
    return VoiceSetup(testbed, business, contact, conversation)
