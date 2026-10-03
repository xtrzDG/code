"""In-memory world for operations tests: repositories, fakes and use cases."""

from app.transformers.notifications.handoff_customer_message_transformer import (
    HandoffCustomerMessageTransformer,
)
from app.transformers.notifications.handoff_notification_transformer import (
    HandoffNotificationTransformer,
)
from app.transformers.notifications.new_lead_notification_transformer import (
    NewLeadNotificationTransformer,
)
from app.transformers.notifications.staff_alert_brief_transformer import (
    StaffAlertBriefTransformer,
)
from app.use_cases.handoffs.answer_unanswered_question_use_case import (
    AnswerUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.handoff_to_human_use_case import HandoffToHumanUseCase
from app.use_cases.handoffs.list_handoffs_use_case import ListHandoffsUseCase
from app.use_cases.handoffs.list_unanswered_questions_use_case import (
    ListUnansweredQuestionsUseCase,
)
from app.use_cases.handoffs.record_unanswered_question_use_case import (
    RecordUnansweredQuestionUseCase,
)
from app.use_cases.handoffs.resolve_handoff_use_case import ResolveHandoffUseCase
from app.use_cases.inbox.assignment.auto_assign_conversation_use_case import (
    AutoAssignConversationUseCase,
)
from app.use_cases.inbox.assignment.refresh_open_request_use_case import (
    RefreshOpenRequestUseCase,
)
from app.use_cases.insights.get_attention_counts_use_case import (
    GetAttentionCountsUseCase,
)
from app.use_cases.insights.get_dashboard_stats_use_case import GetDashboardStatsUseCase
from app.use_cases.insights.get_inbox_counts_use_case import GetInboxCountsUseCase
from app.use_cases.leads.create_lead_use_case import CreateLeadUseCase
from app.use_cases.leads.list_leads_use_case import ListLeadsUseCase
from app.use_cases.leads.update_lead_status_use_case import UpdateLeadStatusUseCase
from tests.operations.operations_booking_factories import OperationsBookingFactories


class OperationsWorld(OperationsBookingFactories):
    """Everything the operations use cases need, wired in memory."""

    def create_lead(self) -> CreateLeadUseCase:
        return CreateLeadUseCase(
            business_repo=self.business_repo,
            lead_repo=self.lead_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            phone_number_parser=self.phone_parser,
            staff_notification_transformer=NewLeadNotificationTransformer(
                self.resolver
            ),
            live_events=self.live_events,
            staff_brief_transformer=StaffAlertBriefTransformer(self.resolver),
            staff_alerts=self.staff_alerts,
            wall_clock=self.clock.wall_clock,
            refresh_open_request=self.refresh_open_request(),
            auto_assign=self.auto_assign(),
        )

    def refresh_open_request(self) -> RefreshOpenRequestUseCase:
        return RefreshOpenRequestUseCase(
            conversation_repo=self.conversation_repo,
            inbox_work_repo=self.inbox_work_repo,
            wall_clock=self.clock.wall_clock,
        )

    def auto_assign(self) -> AutoAssignConversationUseCase:
        return AutoAssignConversationUseCase(
            business_repo=self.business_repo,
            conversation_repo=self.conversation_repo,
            inbox_settings_repo=self.inbox_settings_repo,
            audit_log_repo=self.audit_repo,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def list_leads(self) -> ListLeadsUseCase:
        return ListLeadsUseCase(
            business_repo=self.business_repo,
            lead_repo=self.lead_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
        )

    def update_lead_status(self) -> UpdateLeadStatusUseCase:
        return UpdateLeadStatusUseCase(
            lead_repo=self.lead_repo,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
            refresh_open_request=self.refresh_open_request(),
        )

    def handoff_to_human(self) -> HandoffToHumanUseCase:
        return HandoffToHumanUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            conversation_repo=self.conversation_repo,
            contact_repo=self.contact_repo,
            handoff_repo=self.handoff_repo,
            phone_number_parser=self.phone_parser,
            staff_notification_transformer=HandoffNotificationTransformer(
                self.resolver
            ),
            customer_message_transformer=HandoffCustomerMessageTransformer(
                self.resolver
            ),
            live_events=self.live_events,
            staff_brief_transformer=StaffAlertBriefTransformer(self.resolver),
            staff_alerts=self.staff_alerts,
            wall_clock=self.clock.wall_clock,
        )

    def resolve_handoff(self) -> ResolveHandoffUseCase:
        return ResolveHandoffUseCase(
            handoff_repo=self.handoff_repo,
            conversation_repo=self.conversation_repo,
            contact_repo=self.contact_repo,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def list_handoffs(self) -> ListHandoffsUseCase:
        return ListHandoffsUseCase(
            business_repo=self.business_repo,
            handoff_repo=self.handoff_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
        )

    def record_unanswered_question(self) -> RecordUnansweredQuestionUseCase:
        return RecordUnansweredQuestionUseCase(
            business_repo=self.business_repo,
            unanswered_question_repo=self.question_repo,
            wall_clock=self.clock.wall_clock,
        )

    def list_unanswered_questions(self) -> ListUnansweredQuestionsUseCase:
        return ListUnansweredQuestionsUseCase(
            unanswered_question_repo=self.question_repo
        )

    def answer_unanswered_question(self) -> AnswerUnansweredQuestionUseCase:
        return AnswerUnansweredQuestionUseCase(
            unanswered_question_repo=self.question_repo,
            knowledge_item_repo=self.knowledge_repo,
            wall_clock=self.clock.wall_clock,
        )

    def inbox_counts(self) -> GetInboxCountsUseCase:
        return GetInboxCountsUseCase(
            business_repo=self.business_repo,
            attention_count_repo=self.attention_count_repo,
        )

    def get_attention_counts(self) -> GetAttentionCountsUseCase:
        return GetAttentionCountsUseCase(
            business_repo=self.business_repo,
            attention_count_repo=self.attention_count_repo,
            wall_clock=self.clock.wall_clock,
        )

    def dashboard(self) -> GetDashboardStatsUseCase:
        return GetDashboardStatsUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            conversation_repo=self.conversation_repo,
            message_repo=self.message_repo,
            booking_repo=self.booking_repo,
            lead_repo=self.lead_repo,
            handoff_repo=self.handoff_repo,
            unanswered_question_repo=self.question_repo,
            usage_event_repo=self.usage_repo,
            subscription_repo=self.subscription_repo,
            plan_registry=self.plan_registry,
            wall_clock=self.clock.wall_clock,
        )
