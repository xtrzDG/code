from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.dto.conversations import LlmToolDefinition
from app.schemas.typings.assistants.strings import SystemPromptText, VoiceAgentId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag


class VoiceGreeting(ImmutableDTO):
    """First phrase of a call in one language."""

    language: LanguageTag
    text: MessageText


class VoiceAgentSpec(ImmutableDTO):
    """
    Everything the voice platform needs to create or update the agent of one
    business (concept section 4: same instruction and tools as the chat).
    """

    business_id: BusinessId
    existing_agent_id: VoiceAgentId | None = None
    business_name: BusinessName
    languages: list[LanguageTag]
    default_language: LanguageTag
    prompt_text: SystemPromptText
    greetings: list[VoiceGreeting]
    tools: list[LlmToolDefinition] = Field(default_factory=list[LlmToolDefinition])
    tool_webhook_base_url: PublicBaseUrl
