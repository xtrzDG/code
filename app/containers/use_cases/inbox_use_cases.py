from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory

from app.containers.facilitators import FacilitatorsContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.transformers import TransformersContainer
from app.containers.use_cases.account_use_cases import AccountUseCasesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.inbox.assignment import (
    AssignConversationCommand,
    AutoAssignCommand,
    AutoAssignResult,
    ConversationAssignmentView,
    OpenRequestRefresh,
    OpenRequestState,
)
from app.schemas.dto.inbox.conversation_notes import (
    ConversationNotePage,
    ConversationNotesQuery,
    ConversationNoteView,
    CreateConversationNoteCommand,
    DeleteConversationNoteCommand,
    DeletedConversationNote,
)
from app.schemas.dto.inbox.inbox_settings import (
    InboxSettingsQuery,
    InboxSettingsView,
    UpdateInboxSettingsCommand,
)
from app.schemas.dto.inbox.inbox_views import (
    InboxAssigneeList,
    InboxAssigneesQuery,
    InboxPage,
    InboxQuery,
    InboxViewCounts,
    InboxViewCountsQuery,
)
from app.schemas.dto.inbox.quick_replies import (
    ConversationQuickRepliesQuery,
    DeleteQuickReplyCommand,
    FilledQuickReplyList,
    QuickRepliesQuery,
    QuickReplyList,
    QuickReplyView,
    SaveQuickReplyCommand,
)
from app.use_cases.inbox.assignment.assign_conversation_use_case import (
    AssignConversationUseCase,
)
from app.use_cases.inbox.assignment.auto_assign_conversation_use_case import (
    AutoAssignConversationUseCase,
)
from app.use_cases.inbox.assignment.refresh_open_request_use_case import (
    RefreshOpenRequestUseCase,
)
from app.use_cases.inbox.notes.create_conversation_note_use_case import (
    CreateConversationNoteUseCase,
)
from app.use_cases.inbox.notes.delete_conversation_note_use_case import (
    DeleteConversationNoteUseCase,
)
from app.use_cases.inbox.notes.list_conversation_notes_use_case import (
    ListConversationNotesUseCase,
)
from app.use_cases.inbox.quick_replies.delete_quick_reply_use_case import (
    DeleteQuickReplyUseCase,
)
from app.use_cases.inbox.quick_replies.fill_quick_replies_use_case import (
    FillQuickRepliesUseCase,
)
from app.use_cases.inbox.quick_replies.list_quick_replies_use_case import (
    ListQuickRepliesUseCase,
)
from app.use_cases.inbox.quick_replies.save_quick_reply_use_case import (
    SaveQuickReplyUseCase,
)
from app.use_cases.inbox.settings.get_inbox_settings_use_case import (
    GetInboxSettingsUseCase,
)
from app.use_cases.inbox.settings.update_inbox_settings_use_case import (
    UpdateInboxSettingsUseCase,
)
from app.use_cases.inbox.views.count_inbox_views_use_case import (
    CountInboxViewsUseCase,
)
from app.use_cases.inbox.views.list_inbox_assignees_use_case import (
    ListInboxAssigneesUseCase,
)
from app.use_cases.inbox.views.list_inbox_use_case import ListInboxUseCase


class InboxUseCasesContainer(containers.DeclarativeContainer):
    """
    The team inbox: its views and counts, assignment (manual and
    automatic), the open-request bookkeeping of leads and the inbox
    settings, and what the team writes: internal notes and saved replies.
    """

    facilitators: FacilitatorsContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    transformers: TransformersContainer = DependenciesContainer()  # type: ignore[assignment]
    account_use_cases: AccountUseCasesContainer = DependenciesContainer()  # type: ignore[assignment]

    list_inbox_use_case: Factory[UseCaseContract[InboxQuery, InboxPage]] = Factory(
        ListInboxUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        message_repo=repositories.message_repo,
        note_repo=repositories.conversation_note_repo,
        inbox_work_repo=repositories.inbox_work_repo,
        item_transformer=transformers.inbox_item_transformer,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    count_inbox_views_use_case: Factory[
        UseCaseContract[InboxViewCountsQuery, InboxViewCounts]
    ] = Factory(
        CountInboxViewsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
    )
    list_inbox_assignees_use_case: Factory[
        UseCaseContract[InboxAssigneesQuery, InboxAssigneeList]
    ] = Factory(
        ListInboxAssigneesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        user_repo=repositories.user_repo,
    )
    assign_conversation_use_case: Factory[
        UseCaseContract[AssignConversationCommand, ConversationAssignmentView]
    ] = Factory(
        AssignConversationUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        audit_log_repo=repositories.audit_log_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    auto_assign_conversation_use_case: Factory[
        UseCaseContract[AutoAssignCommand, AutoAssignResult]
    ] = Factory(
        AutoAssignConversationUseCase,
        business_repo=repositories.business_repo,
        conversation_repo=repositories.conversation_repo,
        inbox_settings_repo=repositories.inbox_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    refresh_open_request_use_case: Factory[
        UseCaseContract[OpenRequestRefresh, OpenRequestState]
    ] = Factory(
        RefreshOpenRequestUseCase,
        conversation_repo=repositories.conversation_repo,
        inbox_work_repo=repositories.inbox_work_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    get_inbox_settings_use_case: Factory[
        UseCaseContract[InboxSettingsQuery, InboxSettingsView]
    ] = Factory(
        GetInboxSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        inbox_settings_repo=repositories.inbox_settings_repo,
    )
    update_inbox_settings_use_case: Factory[
        UseCaseContract[UpdateInboxSettingsCommand, InboxSettingsView]
    ] = Factory(
        UpdateInboxSettingsUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        inbox_settings_repo=repositories.inbox_settings_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )

    create_conversation_note_use_case: Factory[
        UseCaseContract[CreateConversationNoteCommand, ConversationNoteView]
    ] = Factory(
        CreateConversationNoteUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        note_repo=repositories.conversation_note_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_conversation_notes_use_case: Factory[
        UseCaseContract[ConversationNotesQuery, ConversationNotePage]
    ] = Factory(
        ListConversationNotesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        note_repo=repositories.conversation_note_repo,
        user_repo=repositories.user_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    delete_conversation_note_use_case: Factory[
        UseCaseContract[DeleteConversationNoteCommand, DeletedConversationNote]
    ] = Factory(
        DeleteConversationNoteUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        note_repo=repositories.conversation_note_repo,
        audit_log_repo=repositories.audit_log_repo,
        live_events=facilitators.event_publisher,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    list_quick_replies_use_case: Factory[
        UseCaseContract[QuickRepliesQuery, QuickReplyList]
    ] = Factory(
        ListQuickRepliesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        quick_reply_library_repo=repositories.quick_reply_library_repo,
    )
    save_quick_reply_use_case: Factory[
        UseCaseContract[SaveQuickReplyCommand, QuickReplyView]
    ] = Factory(
        SaveQuickReplyUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        quick_reply_library_repo=repositories.quick_reply_library_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    delete_quick_reply_use_case: Factory[
        UseCaseContract[DeleteQuickReplyCommand, QuickReplyList]
    ] = Factory(
        DeleteQuickReplyUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        quick_reply_library_repo=repositories.quick_reply_library_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    fill_quick_replies_use_case: Factory[
        UseCaseContract[ConversationQuickRepliesQuery, FilledQuickReplyList]
    ] = Factory(
        FillQuickRepliesUseCase,
        authorize_business_access=account_use_cases.authorize_business_access_use_case,
        conversation_repo=repositories.conversation_repo,
        contact_repo=repositories.contact_repo,
        booking_repo=repositories.booking_repo,
        quick_reply_library_repo=repositories.quick_reply_library_repo,
        audit_log_repo=repositories.audit_log_repo,
        wall_clock=time_provider.microsecond_wall_clock,
    )
