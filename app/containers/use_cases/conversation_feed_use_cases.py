from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.container_edges import composed_container_edge
from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.call_recordings import CallRecordingQuery, RecordingPart
from app.schemas.dto.conversation_feed.conversation_actions import (
    RateConversationCommand,
    SendStaffMessageCommand,
    StaffMessageResult,
)
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationDetailView,
    ConversationListQuery,
    ConversationMessagesQuery,
    ConversationPage,
    ConversationQuery,
    ConversationSummaryView,
    MessagePage,
)
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatVersionQuery
from app.schemas.dto.media import MessageMediaQuery, StoredMediaFile
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.use_cases.conversations.card.list_conversation_messages_use_case import (
    ListConversationMessagesUseCase,
)
from app.use_cases.conversations.get_call_recording_use_case import (
    GetCallRecordingUseCase,
)
from app.use_cases.conversations.get_conversation_use_case import GetConversationUseCase
from app.use_cases.conversations.get_message_media_use_case import (
    GetMessageMediaUseCase,
)
from app.use_cases.conversations.list_conversations_use_case import (
    ListConversationsUseCase,
)
from app.use_cases.conversations.rate_conversation_use_case import (
    RateConversationUseCase,
)
from app.use_cases.conversations.resolve_test_chat_version_use_case import (
    ResolveTestChatVersionUseCase,
)
from app.use_cases.conversations.send_staff_message_use_case import (
    SendStaffMessageUseCase,
)


class ConversationFeedUseCasesContainer(containers.DeclarativeContainer):
    """
    The cabinet's conversation feed: conversations, call recordings, staff
    messages, ratings, and the version the owner's test chat talks to.
    """

    adapters: AdaptersContainer = composed_container_edge(AdaptersContainer)  # type: ignore[assignment]
    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_conversations_use_case: Factory[
        UseCaseContract[ConversationListQuery, ConversationPage]
    ] = Factory(
        ListConversationsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        summary_transformer=transformers.conversation_summary_transformer,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_conversation_use_case: Factory[
        UseCaseContract[ConversationQuery, ConversationDetailView]
    ] = Factory(
        GetConversationUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        audit_log_repo=repositories.audit_log_repo,
        summary_transformer=transformers.conversation_summary_transformer,
        message_transformer=transformers.message_view_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
        call_repo=repositories.call_repo,
        call_transformer=transformers.call_view_transformer,
        booking_repo=repositories.booking_repo,
        lead_repo=repositories.lead_repo,
        handoff_repo=repositories.handoff_repo,
        resource_repo=repositories.resource_repo,
        channel_repo=repositories.channel_repo,
        outbound_message_repo=repositories.outbound_message_repo,
    )
    list_conversation_messages_use_case: Factory[
        UseCaseContract[ConversationMessagesQuery, MessagePage]
    ] = Factory(
        ListConversationMessagesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        message_transformer=transformers.message_view_transformer,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
        outbound_message_repo=repositories.outbound_message_repo,
    )
    get_message_media_use_case: Factory[
        UseCaseContract[MessageMediaQuery, StoredMediaFile]
    ] = Factory(
        GetMessageMediaUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        message_media_repo=repositories.message_media_repo,
        media_storage=adapters.media.media_storage,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_call_recording_use_case: Factory[
        UseCaseContract[CallRecordingQuery, RecordingPart]
    ] = Factory(
        GetCallRecordingUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        call_repo=repositories.call_repo,
        recording_storage=adapters.recording_storage,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    send_staff_message_use_case: Factory[
        UseCaseContract[SendStaffMessageCommand, StaffMessageResult]
    ] = Factory(
        SendStaffMessageUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        message_repo=repositories.message_repo,
        channel_repo=repositories.channel_repo,
        audit_log_repo=repositories.audit_log_repo,
        outbound_message_repo=repositories.outbound_message_repo,
        job_queue=facilitators.job_queue_facilitator,
        message_transformer=transformers.message_view_transformer,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
        unit_of_work=adapters.storage_unit_of_work,
    )
    rate_conversation_use_case: Factory[
        UseCaseContract[RateConversationCommand, ConversationSummaryView]
    ] = Factory(
        RateConversationUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        summary_transformer=transformers.conversation_summary_transformer,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    resolve_test_chat_version_use_case: Factory[
        UseCaseContract[OwnerTestChatVersionQuery, AssistantVersionId]
    ] = Factory(
        ResolveTestChatVersionUseCase,
        assistant_version_repo=repositories.assistant_version_repo,
    )
