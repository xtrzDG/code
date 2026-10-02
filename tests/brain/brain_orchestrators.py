"""The real text and voice orchestrators of a brain test world."""

from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.llm import LlmAdapterContract
from app.orchestrators.conversations.conversation_turn_orchestrator import (
    ConversationTurnOrchestrator,
)
from app.orchestrators.conversations.voice_tool_call_orchestrator import (
    VoiceToolCallOrchestrator,
)
from app.registries.billing.plan_registry import PlanRegistry
from app.registries.tools.assistant_tool_registry import AssistantToolRegistry
from app.schemas.constants.assistants import LlmEffort
from app.schemas.typings.assistants.constrained_integers import (
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.conversations.constrained_integers import (
    ContactMessageLimit,
)
from app.use_cases.conversations.open_voice_conversation_use_case import (
    OpenVoiceConversationUseCase,
)
from app.use_cases.conversations.record_assistant_reply_use_case import (
    RecordAssistantReplyUseCase,
)
from app.use_cases.conversations.record_voice_tool_call_use_case import (
    RecordVoiceToolCallUseCase,
)
from app.use_cases.conversations.replies.generate_assistant_reply_use_case import (
    GenerateAssistantReplyUseCase,
)
from app.use_cases.conversations.turns.prepare_conversation_turn_use_case import (
    PrepareConversationTurnUseCase,
)
from app.utilities.conversations.language_detector import LanguageDetector
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.brain.brain_repositories import BrainRepositories
from tests.brain.brain_tools import BrainTools


@dataclass(frozen=True)
class BrainOrchestrators:
    orchestrator: ConversationTurnOrchestrator
    voice_orchestrator: VoiceToolCallOrchestrator


def build_brain_orchestrators(
    llm: LlmAdapterContract,
    repos: BrainRepositories,
    tools: BrainTools,
    texts: LocalizedTextResolver,
    wall_clock: WallClock[Microseconds],
    *,
    contact_message_limit: int,
    tool_round_limit: int,
) -> BrainOrchestrators:
    storage_scope = StorageScopeContext()
    orchestrator = ConversationTurnOrchestrator(
        prepare_turn=PrepareConversationTurnUseCase(
            business_repo=repos.business_repo,
            business_profile_repo=repos.profile_repo,
            schedule_exception_repo=repos.exception_repo,
            assistant_version_repo=repos.version_repo,
            contact_repo=repos.contact_repo,
            conversation_repo=repos.conversation_repo,
            message_repo=repos.message_repo,
            language_detector=LanguageDetector(),
            wall_clock=wall_clock,
            contact_message_limit=ContactMessageLimit(contact_message_limit),
        ),
        generate_reply=GenerateAssistantReplyUseCase(
            llm_adapter=llm,
            llm_turn_repo=repos.llm_turn_repo,
            message_repo=repos.message_repo,
            tool_registry=AssistantToolRegistry(),
            run_assistant_tool=tools.run_tool,
            wall_clock=wall_clock,
            max_output_tokens=LlmMaxOutputTokens(4000),
            effort=LlmEffort.LOW,
            tool_round_limit=LlmToolRoundLimit(tool_round_limit),
        ),
        handoff_to_human=tools.handoff,
        record_reply=RecordAssistantReplyUseCase(
            message_repo=repos.message_repo,
            conversation_repo=repos.conversation_repo,
            usage_event_repo=repos.usage_event_repo,
            localized_text_resolver=texts,
            wall_clock=wall_clock,
        ),
        localized_text_resolver=texts,
        storage_scope=storage_scope,
    )
    voice_orchestrator = VoiceToolCallOrchestrator(
        open_voice_conversation=OpenVoiceConversationUseCase(
            business_repo=repos.business_repo,
            assistant_version_repo=repos.version_repo,
            contact_repo=repos.contact_repo,
            conversation_repo=repos.conversation_repo,
            channel_repo=repos.channel_repo,
            plan_registry=PlanRegistry(),
            wall_clock=wall_clock,
        ),
        run_assistant_tool=tools.run_tool,
        record_voice_tool_call=RecordVoiceToolCallUseCase(
            message_repo=repos.message_repo,
            wall_clock=wall_clock,
        ),
        storage_scope=storage_scope,
    )
    return BrainOrchestrators(
        orchestrator=orchestrator, voice_orchestrator=voice_orchestrator
    )
