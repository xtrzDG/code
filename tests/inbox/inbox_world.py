"""The use cases of the team inbox, wired over the in-memory store."""

from app.transformers.inbox.inbox_item_transformer import InboxItemTransformer
from app.use_cases.authorize_business_access_use_case import (
    AuthorizeBusinessAccessUseCase,
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
from tests.inbox.inbox_store import InboxStore


class InboxWorld(InboxStore):
    """Every inbox use case over the store (fresh instances on each call)."""

    def authorize(self) -> AuthorizeBusinessAccessUseCase:
        return AuthorizeBusinessAccessUseCase(
            business_repo=self.business_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )

    def list_inbox(self) -> ListInboxUseCase:
        return ListInboxUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
            contact_repo=self.contact_repo,
            message_repo=self.message_repo,
            note_repo=self.note_repo,
            inbox_work_repo=self.inbox_work_repo,
            item_transformer=InboxItemTransformer(),
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )

    def count_views(self) -> CountInboxViewsUseCase:
        return CountInboxViewsUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
        )

    def list_assignees(self) -> ListInboxAssigneesUseCase:
        return ListInboxAssigneesUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
            user_repo=self.user_repo,
        )

    def assign(self) -> AssignConversationUseCase:
        return AssignConversationUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
            audit_log_repo=self.audit_log_repo,
            live_events=self.live_events,
            wall_clock=self.wall_clock,
        )

    def auto_assign(self) -> AutoAssignConversationUseCase:
        return AutoAssignConversationUseCase(
            business_repo=self.business_repo,
            conversation_repo=self.conversation_repo,
            inbox_settings_repo=self.settings_repo,
            audit_log_repo=self.audit_log_repo,
            live_events=self.live_events,
            wall_clock=self.wall_clock,
        )

    def refresh_open_request(self) -> RefreshOpenRequestUseCase:
        return RefreshOpenRequestUseCase(
            conversation_repo=self.conversation_repo,
            inbox_work_repo=self.inbox_work_repo,
            wall_clock=self.wall_clock,
        )

    def get_settings(self) -> GetInboxSettingsUseCase:
        return GetInboxSettingsUseCase(
            authorize_business_access=self.authorize(),
            inbox_settings_repo=self.settings_repo,
        )

    def update_settings(self) -> UpdateInboxSettingsUseCase:
        return UpdateInboxSettingsUseCase(
            authorize_business_access=self.authorize(),
            inbox_settings_repo=self.settings_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )

    def create_note(self) -> CreateConversationNoteUseCase:
        return CreateConversationNoteUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
            note_repo=self.note_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            live_events=self.live_events,
            wall_clock=self.wall_clock,
        )

    def list_notes(self) -> ListConversationNotesUseCase:
        return ListConversationNotesUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
            note_repo=self.note_repo,
            user_repo=self.user_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )

    def delete_note(self) -> DeleteConversationNoteUseCase:
        return DeleteConversationNoteUseCase(
            authorize_business_access=self.authorize(),
            note_repo=self.note_repo,
            audit_log_repo=self.audit_log_repo,
            live_events=self.live_events,
            wall_clock=self.wall_clock,
        )

    def list_quick_replies(self) -> ListQuickRepliesUseCase:
        return ListQuickRepliesUseCase(
            authorize_business_access=self.authorize(),
            quick_reply_library_repo=self.quick_reply_repo,
        )

    def save_quick_reply(self) -> SaveQuickReplyUseCase:
        return SaveQuickReplyUseCase(
            authorize_business_access=self.authorize(),
            quick_reply_library_repo=self.quick_reply_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )

    def delete_quick_reply(self) -> DeleteQuickReplyUseCase:
        return DeleteQuickReplyUseCase(
            authorize_business_access=self.authorize(),
            quick_reply_library_repo=self.quick_reply_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )

    def fill_quick_replies(self) -> FillQuickRepliesUseCase:
        return FillQuickRepliesUseCase(
            authorize_business_access=self.authorize(),
            conversation_repo=self.conversation_repo,
            contact_repo=self.contact_repo,
            booking_repo=self.booking_repo,
            quick_reply_library_repo=self.quick_reply_repo,
            audit_log_repo=self.audit_log_repo,
            wall_clock=self.wall_clock,
        )
