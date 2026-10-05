
from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
    ConversationMemoryRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.customer_memory.assistant_settings import (
    AssistantSettingsView,
)
from app.schemas.dto.customer_memory.returning_customers import (
    CustomerMemory,
    CustomerMemoryRequest,
    ReturningCustomerContext,
)
from app.schemas.typings.conversations.constrained_integers import (
    EarlierConversationCount,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.conversations.memory.memory_reading import (
    MAX_UPCOMING_BOOKINGS,
    RECALLED_CONVERSATION_COUNT,
    open_leads,
    remembered_summaries,
    team_notes,
)
from app.use_cases.shared.customer_bookings import find_customer_bookings
from app.utilities.memory.assistant_settings_views import view_assistant_settings
from app.utilities.memory.summary_jobs import (
    SUMMARIZE_CONVERSATION_JOB,
    encode_summary_payload,
    starts_active_period,
    summary_due_at,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.zoned_time import microseconds_to_seconds

NO_MEMORY: CustomerMemory = CustomerMemory()


class RecallCustomerMemoryUseCase(
    UseCaseContract[CustomerMemoryRequest, CustomerMemory]
):
    """
    The assistant's memory of the customer behind one message (the
    customer-and-AI concept: a service remembers its guests).

    When the message starts an active period of the conversation (a new
    conversation, or one quiet for two hours), the conversation's summary
    job is queued for two hours later (`summarize_conversation`, default
    lane). On the turn that opens the assistant's part of the conversation
    the memory is read, all within the business: how many conversations the
    customer had before and when the last was, what the three latest
    summarized ones were about, their bookings still to come and the
    requests staff have not closed, and, when the owner shares them, the
    team's notes on their latest conversations.

    Nothing is remembered or queued for sandbox conversations (owner tests),
    an erased customer, or a business that turned customer memory off
    (Settings → General).
    """

    def __init__(
        self,
        assistant_settings_repo: AssistantSettingsRepoContract,
        conversation_memory_repo: ConversationMemoryRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        note_repo: ConversationNoteRepoContract,
        job_queue: JobQueueFacilitatorContract,
    ) -> None:
        self._assistant_settings_repo: AssistantSettingsRepoContract = (
            assistant_settings_repo
        )
        self._conversation_memory_repo: ConversationMemoryRepoContract = (
            conversation_memory_repo
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._note_repo: ConversationNoteRepoContract = note_repo
        self._job_queue: JobQueueFacilitatorContract = job_queue

    def run(self, input_data: CustomerMemoryRequest) -> CustomerMemory:
        conversation: ConversationDocument = input_data.conversation
        if conversation.is_sandbox or input_data.contact.erased_at is not None:
            return NO_MEMORY

        settings: AssistantSettingsView = view_assistant_settings(
            self._assistant_settings_repo.get_by_business(input_data.business.id)
        )
        if not settings.remembers_customers:
            return NO_MEMORY

        if starts_active_period(input_data.previous_last_message_at, input_data.now):
            self._job_queue.enqueue(
                SUMMARIZE_CONVERSATION_JOB,
                encode_summary_payload(conversation.id),
                input_data.business.id,
                run_at=summary_due_at(input_data.now),
            )

        if not input_data.wants_context:
            return NO_MEMORY

        context: ReturningCustomerContext = self._recall(
            input_data, settings.shares_team_notes
        )
        return NO_MEMORY if context.is_empty else CustomerMemory(context=context)

    def _recall(
        self,
        input_data: CustomerMemoryRequest,
        shares_team_notes: bool,
    ) -> ReturningCustomerContext:
        business_id = input_data.business.id
        earlier: list[ConversationDocument] = [
            conversation
            for conversation in self._conversation_memory_repo.list_latest_by_contact(
                business_id,
                input_data.contact.id,
                DocumentQueryLimit(RECALLED_CONVERSATION_COUNT),
            )
            if conversation.id != input_data.conversation.id
            and not conversation.is_sandbox
        ]
        counted: int = int(
            self._conversation_memory_repo.count_by_contact(
                business_id, input_data.contact.id
            )
        )
        return ReturningCustomerContext(
            earlier_conversation_count=EarlierConversationCount(
                max(counted - 1, len(earlier), 0)
            ),
            last_visit_at=earlier[0].last_message_at if earlier else None,
            summaries=remembered_summaries(earlier),
            upcoming_bookings=find_customer_bookings(
                self._booking_repo,
                self._resource_repo,
                self._knowledge_item_repo,
                input_data.business,
                {input_data.contact.id},
                BLOCKING_BOOKING_STATUSES,
                is_sandbox=False,
                now_seconds=microseconds_to_seconds(int(input_data.now)),
            )[:MAX_UPCOMING_BOOKINGS],
            open_leads=open_leads(
                self._lead_repo, business_id, [input_data.conversation, *earlier]
            ),
            team_notes=(
                team_notes(self._note_repo, business_id, earlier)
                if shares_team_notes
                else []
            ),
        )
