from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.registries.demo.demo_clock import DemoClock
from app.registries.demo.demo_conversation_recorder import DemoConversationRecorder
from app.registries.demo.demo_feedback import (
    build_demo_feedback_requests,
    build_demo_review_settings,
)
from app.registries.demo.demo_operations_recorder import DemoOperationsRecorder
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.domain.billing import (
    InvoiceDocument,
    SubscriptionDocument,
    UsageEventDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.package_usage import PackageUsageWarningDocument
from app.schemas.dto.demo_data import DemoActivityRequest, DemoBusinessActivity
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.inbox.constrained_integers import AssignmentRevision
from app.schemas.typings.users.prefixed_id import UserId

# The owner assigns a conversation that needs a person this soon.
ASSIGNED_AFTER_MINUTES: int = 7


class DemoActivityBuilder:
    """
    The story of one demo business, written by its content module:
    `talk` records customers and conversations, `desk` what they asked for
    (bookings, leads, handoffs, questions); `finish` adds billing and the
    autotest run of the published version.
    """

    def __init__(self, request: DemoActivityRequest) -> None:
        business: BusinessDocument = request.foundation.business
        self.business: BusinessDocument = business
        self.clock: DemoClock = DemoClock(request.now, business.timezone)
        self.published_version_id: AssistantVersionId = find_published_version(request)
        self.owner_id: UserId = find_member(business, BusinessMemberRole.OWNER)
        staff_ids: list[UserId] = [
            member.user_id
            for member in business.members
            if member.role is BusinessMemberRole.STAFF
        ]
        # Staff replies in the cabinet come from the staff member when the
        # business has one, otherwise from the owner.
        self.team_member_id: UserId = staff_ids[0] if staff_ids else self.owner_id
        self.talk: DemoConversationRecorder = DemoConversationRecorder(
            business=business,
            clock=self.clock,
            hours=list(request.foundation.profile.hours),
            schedule_exceptions=list(request.foundation.schedule_exceptions),
            live_versions=list_live_versions(request),
            model_id=request.model_id,
            team_member_id=self.team_member_id,
        )
        self._knowledge_items: list[KnowledgeItemDocument] = list(
            request.foundation.knowledge_items
        )
        self.desk: DemoOperationsRecorder = DemoOperationsRecorder(
            business=business,
            clock=self.clock,
            resources=list(request.foundation.resources),
        )

    def item(self, title_start: str) -> KnowledgeItemDocument:
        """The knowledge item whose title starts with `title_start`."""

        for item in self._knowledge_items:
            if str(item.title).startswith(title_start):
                return item

        raise ValueError(f"The demo business has no knowledge item {title_start!r}.")

    def finish(
        self,
        subscription: SubscriptionDocument,
        usage_events: Sequence[UsageEventDocument],
        autotest_run: AutotestRunDocument,
        invoices: Sequence[InvoiceDocument] = (),
        package_usage_warnings: Sequence[PackageUsageWarningDocument] = (),
        audit_log_entries: Sequence[AuditLogEntryDocument] = (),
    ) -> DemoBusinessActivity:
        self._assign_oldest_waiting_conversation()
        return DemoBusinessActivity(
            contacts=self.talk.contacts,
            conversations=self.talk.conversations,
            messages=self.talk.messages,
            calls=self.talk.calls,
            bookings=self.desk.bookings,
            leads=self.desk.leads,
            handoffs=self.desk.handoffs,
            unanswered_questions=self.desk.questions,
            subscription=subscription,
            invoices=list(invoices),
            usage_events=list(usage_events),
            package_usage_warnings=list(package_usage_warnings),
            audit_log_entries=list(audit_log_entries),
            autotest_run=autotest_run,
            review_settings=build_demo_review_settings(self.business, self.clock.now),
            feedback_requests=build_demo_feedback_requests(
                self.business, self.desk.bookings, self.talk.contacts, self.clock.now
            ),
        )

    def _assign_oldest_waiting_conversation(self) -> None:
        """
        The team inbox as a business uses it: the owner gave the oldest
        conversation that needs a person to the staff member a few minutes
        after the handoff (newer ones still wait unassigned).
        """

        if self.team_member_id == self.owner_id:
            return

        waiting: list[ConversationDocument] = sorted(
            (
                conversation
                for conversation in self.talk.conversations
                if conversation.status is ConversationStatus.HANDOFF
                and not conversation.is_sandbox
            ),
            key=lambda conversation: int(conversation.last_message_at),
        )
        if not waiting:
            return

        oldest: ConversationDocument = waiting[0]
        oldest.assignee_user_id = self.team_member_id
        oldest.assigned_by = self.owner_id
        oldest.assigned_at = Microseconds(
            min(
                int(self.clock.later(oldest.last_message_at, ASSIGNED_AFTER_MINUTES)),
                int(self.clock.now),
            )
        )
        oldest.assignment_revision = AssignmentRevision(1)


def list_live_versions(
    request: DemoActivityRequest,
) -> list[tuple[Microseconds, AssistantVersionId]]:
    """(went live at, version id) of every version that was ever published."""

    return [
        (plan.published_at, version_id)
        for plan, version_id in zip(
            request.foundation.assistant_versions, request.version_ids, strict=True
        )
        if plan.published_at is not None
    ]


def find_published_version(request: DemoActivityRequest) -> AssistantVersionId:
    for plan, version_id in zip(
        request.foundation.assistant_versions, request.version_ids, strict=True
    ):
        if plan.status is AssistantVersionStatus.PUBLISHED:
            return version_id

    raise ValueError("The demo business has no published assistant version.")


def find_member(business: BusinessDocument, role: BusinessMemberRole) -> UserId:
    for member in business.members:
        if member.role is role:
            return member.user_id

    raise ValueError(f"Demo business {business.name} has no {role.value}.")
