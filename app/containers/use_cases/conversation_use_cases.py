from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.config import ConfigContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.booking_use_cases import BookingUseCasesContainer
from app.containers.use_cases.follow_up_use_cases import FollowUpUseCasesContainer
from app.containers.use_cases.knowledge_use_cases import KnowledgeUseCasesContainer
from app.containers.utilities import UtilitiesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.conversation_engine import (
    GeneratedReply,
    PreparedTurn,
    ReplyRecord,
    VoiceToolCallRecord,
)
from app.schemas.dto.conversations import (
    AssistantReply,
    CallGreeting,
    CallGreetingRequest,
    InboundMessage,
    VoiceToolCallRequest,
    VoiceToolCallResult,
)
from app.schemas.dto.customer_memory.returning_customers import (
    CustomerMemory,
    CustomerMemoryRequest,
)
from app.schemas.dto.media import (
    VoiceNoteTranscription,
    VoiceNoteTranscriptionRequest,
)
from app.use_cases.conversations.build_call_greeting_use_case import (
    BuildCallGreetingUseCase,
)
from app.use_cases.conversations.memory.recall_customer_memory_use_case import (
    RecallCustomerMemoryUseCase,
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
from app.use_cases.conversations.tools.run_assistant_tool_use_case import (
    RunAssistantToolUseCase,
)
from app.use_cases.conversations.transcribe_voice_note_use_case import (
    TranscribeVoiceNoteUseCase,
)
from app.use_cases.conversations.turns.prepare_conversation_turn_use_case import (
    PrepareConversationTurnUseCase,
)


class ConversationUseCasesContainer(containers.DeclarativeContainer):
    """
    The conversation engine: the tools of the assistant, then prepare,
    generate and record a turn; the voice turn's pieces and the call greeting.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]
    knowledge_use_cases: KnowledgeUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    booking_use_cases: BookingUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]
    follow_up_use_cases: FollowUpUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    run_assistant_tool_use_case: Factory[
        UseCaseContract[AssistantToolInvocation, AssistantToolOutcome]
    ] = Factory(
        RunAssistantToolUseCase,
        search_knowledge=knowledge_use_cases.search_knowledge_use_case,
        get_price=knowledge_use_cases.get_price_use_case,
        send_link=knowledge_use_cases.send_link_use_case,
        check_availability=booking_use_cases.check_availability_use_case,
        create_booking=booking_use_cases.create_booking_use_case,
        cancel_booking=booking_use_cases.cancel_booking_use_case,
        reschedule_booking=booking_use_cases.reschedule_booking_use_case,
        list_my_bookings=booking_use_cases.list_customer_bookings_use_case,
        create_lead=follow_up_use_cases.create_lead_use_case,
        handoff_to_human=follow_up_use_cases.handoff_to_human_use_case,
        record_unanswered_question=follow_up_use_cases.record_unanswered_question_use_case,
        phone_number_parser=utilities.phone_number_parser,
        wall_clock=time_provider.microsecond_wall_clock,
        send_booking_confirmation=booking_use_cases.send_booking_confirmation_use_case,
    )
    # What the assistant remembers of a returning customer (1121).
    recall_customer_memory_use_case: Factory[
        UseCaseContract[CustomerMemoryRequest, CustomerMemory]
    ] = Factory(
        RecallCustomerMemoryUseCase,
        assistant_settings_repo=repositories.assistant_settings_repo,
        conversation_memory_repo=repositories.conversation_repo,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        resource_repo=repositories.resource_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        note_repo=repositories.conversation_note_repo,
        job_queue=facilitators.job_queue_facilitator,
    )
    prepare_conversation_turn_use_case: Factory[
        UseCaseContract[InboundMessage, PreparedTurn]
    ] = Factory(
        PrepareConversationTurnUseCase,
        business_repo=repositories.business_repo,
        business_profile_repo=repositories.business_profile_repo,
        schedule_exception_repo=repositories.schedule_exception_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        language_detector=utilities.language_detector,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
        contact_message_limit=config.app_settings.provided.contact_message_limit_per_hour,
        injection_flag_limit=config.app_settings.provided.reply_safety.injection_flag_limit,
        recall_customer_memory=recall_customer_memory_use_case,
    )
    generate_assistant_reply_use_case: Factory[
        UseCaseContract[PreparedTurn, GeneratedReply]
    ] = Factory(
        GenerateAssistantReplyUseCase,
        llm_adapter=adapters.chat_llm_adapter,
        llm_turn_repo=repositories.llm_turn_repo,
        message_repo=repositories.message_repo,
        contact_repo=repositories.contact_repo,
        claim_check=facilitators.claim_check,
        tool_registry=registries.assistant_tool_registry,
        run_assistant_tool=run_assistant_tool_use_case,
        wall_clock=time_provider.microsecond_wall_clock,
        max_output_tokens=config.app_settings.provided.llm_max_output_tokens,
        effort=config.app_settings.provided.llm_chat_effort,
        tool_round_limit=config.app_settings.provided.llm_tool_round_limit,
    )
    record_assistant_reply_use_case: Factory[
        UseCaseContract[ReplyRecord, AssistantReply]
    ] = Factory(
        RecordAssistantReplyUseCase,
        message_repo=repositories.message_repo,
        conversation_repo=repositories.conversation_repo,
        usage_event_repo=repositories.usage_event_repo,
        localized_text_resolver=utilities.localized_text_resolver,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    open_voice_conversation_use_case: Factory[
        UseCaseContract[VoiceToolCallRequest, AssistantToolContext]
    ] = Factory(
        OpenVoiceConversationUseCase,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        contact_repo=repositories.contact_repo,
        conversation_repo=repositories.conversation_repo,
        channel_repo=repositories.channel_repo,
        plan_registry=registries.plan_registry,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    record_voice_tool_call_use_case: Factory[
        UseCaseContract[VoiceToolCallRecord, VoiceToolCallResult]
    ] = Factory(
        RecordVoiceToolCallUseCase,
        message_repo=repositories.message_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    build_call_greeting_use_case: Factory[
        UseCaseContract[CallGreetingRequest, CallGreeting]
    ] = Factory(
        BuildCallGreetingUseCase,
        business_repo=repositories.business_repo,
        localized_text_resolver=utilities.localized_text_resolver,
    )
    # Voice notes and photos customers send: transcription, the cabinet.
    transcribe_voice_note_use_case: Factory[
        UseCaseContract[VoiceNoteTranscriptionRequest, VoiceNoteTranscription]
    ] = Factory(
        TranscribeVoiceNoteUseCase,
        message_media_repo=repositories.message_media_repo,
        media_storage=adapters.media.media_storage,
        voice_transcriber=adapters.media.voice_transcriber,
        business_repo=repositories.business_repo,
        assistant_version_repo=repositories.assistant_version_repo,
        usage_event_repo=repositories.usage_event_repo,
        media_settings=config.app_settings.provided.media,
        wall_clock=time_provider.microsecond_wall_clock,
    )
