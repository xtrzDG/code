"""
What a business's voice agent is built from (publishing, the agents'
re-sync and the voice checks of autotests alike): one version and the
business's data the agent is tuned with.
"""

from dataclasses import dataclass

from app.contracts.assistant_assembly import AssistantToolCatalogContract
from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceProfileRegistryContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.voice_agent_settings import VoiceAgentSettings
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import CallGreeting, CallGreetingRequest
from app.schemas.dto.voice import LanguageVoiceProfile, VoiceAgentSpec, VoiceGreeting
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.shared.assistant_knowledge import load_active_knowledge
from app.utilities.channels.voice_keywords import collect_asr_keywords
from app.utilities.channels.voice_service import find_transfer_phone_number
from app.utilities.conversations.tool_selection import select_voice_agent_tools


@dataclass(frozen=True, slots=True, kw_only=True)
class VoiceAgentSources:
    """
    Where a voice agent's parts come from besides its version: the greeting
    of each language, the tools' definitions, the staff phone of the
    transfer (the profile), the voice of each language, the business's
    items and resources for the speech recognition, and the platform's
    tuning (AppSettings.voice_agents).
    """

    business_profile_repo: BusinessProfileRepoContract
    knowledge_item_repo: KnowledgeItemRepoContract
    brand_knowledge_item_repo: BrandKnowledgeItemRepoContract
    resource_repo: ResourceRepoContract
    build_call_greeting: UseCaseContract[CallGreetingRequest, CallGreeting]
    assistant_tool_catalog: AssistantToolCatalogContract
    voice_profile_registry: VoiceProfileRegistryContract
    app_settings: AppSettings


def build_voice_agent_spec(
    sources: VoiceAgentSources,
    business: BusinessDocument,
    version: AssistantVersionDocument,
    existing_agent_id: VoiceAgentId | None,
    base_url: PublicBaseUrl,
) -> VoiceAgentSpec:
    """
    The agent of one version: its phone instruction (its chat instruction
    for a version assembled before it), a greeting and a voice in every
    language of the version, the tools of `select_voice_agent_tools` behind
    the public base URL of the tool webhooks, the transfer to the
    profile's handoff phone in opening hours, the speech recognition's
    keywords and the platform's model, temperature and turn timeout.
    """

    tuning: VoiceAgentSettings = sources.app_settings.voice_agents
    return VoiceAgentSpec(
        business_id=business.id,
        existing_agent_id=existing_agent_id,
        business_name=business.name,
        languages=list(version.languages),
        default_language=version.default_language,
        prompt_text=version.phone_prompt_text or version.prompt_text,
        greetings=build_greetings(sources, business, version),
        tools=sources.assistant_tool_catalog.list_definitions(
            select_voice_agent_tools(version)
        ),
        tool_webhook_base_url=base_url,
        transfer_phone_number=find_transfer_phone_number(
            business, sources.business_profile_repo.get_by_business(business.id)
        ),
        voice_profiles=[
            LanguageVoiceProfile(
                language=language,
                profile=sources.voice_profile_registry.get(language),
            )
            for language in dict.fromkeys(
                [version.default_language, *version.languages]
            )
        ],
        llm_model=tuning.llm_model,
        temperature=tuning.temperature,
        asr_keywords=collect_asr_keywords(
            business.name,
            sources.resource_repo.list_by_business(business.id),
            load_active_knowledge(
                sources.knowledge_item_repo,
                sources.brand_knowledge_item_repo,
                business,
            ),
            version.languages,
        ),
        turn_timeout_seconds=tuning.turn_timeout_seconds,
    )


def build_greetings(
    sources: VoiceAgentSources,
    business: BusinessDocument,
    version: AssistantVersionDocument,
) -> list[VoiceGreeting]:
    """The greeting of every language of the version, one per language."""

    greetings: list[VoiceGreeting] = []
    for language in version.languages:
        greeting: CallGreeting = sources.build_call_greeting.run(
            CallGreetingRequest(business_id=business.id, language=language)
        )
        if any(existing.language == greeting.language for existing in greetings):
            continue

        greetings.append(VoiceGreeting(language=greeting.language, text=greeting.text))

    return greetings
