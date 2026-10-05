import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
    ConversationMemoryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.customer_memory.conversation_summaries import (
    ConversationSummaryWrite,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.use_cases.conversations.memory.summary_writing import (
    ask_for_summary,
    has_customer_words,
    transcript_lines,
)
from app.utilities.memory.assistant_settings_views import view_assistant_settings
from app.utilities.memory.summary_jobs import (
    SUMMARIZE_CONVERSATION_JOB,
    decode_summary_payload,
    encode_summary_payload,
    summary_due_at,
)
from app.utilities.privacy.erased_conversations import is_erased_conversation

LOGGER: logging.Logger = logging.getLogger(__name__)
NOTHING_DONE: JobReport = JobReport()


class SummarizeConversationUseCase(UseCaseContract[QueuedJobInput, JobReport]):
    """
    Write what one conversation was about once it has been quiet for two
    hours (the queued job `summarize_conversation`, default lane): a cheap
    model (LLM_SUMMARY_MODEL_ID, else the chat model) reads its messages and
    writes at most 300 characters in English, which the assistant reads when
    the customer comes back.

    A conversation that got messages since the job was queued moves the
    job to two hours after its latest message. Nothing is written for a
    sandbox conversation, a business that turned customer memory off, an
    erased visitor (checked again in the write itself, so an erasure that
    runs meanwhile wins), a conversation without words of the customer, or
    one already summarized since its latest message. A failed model call
    is tried again by the job queue; after the last attempt the
    conversation stays without a summary.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        conversation_repo: ConversationRepoContract,
        conversation_memory_repo: ConversationMemoryRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        assistant_settings_repo: AssistantSettingsRepoContract,
        job_queue: JobQueueFacilitatorContract,
        llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._conversation_memory_repo: ConversationMemoryRepoContract = (
            conversation_memory_repo
        )
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._assistant_settings_repo: AssistantSettingsRepoContract = (
            assistant_settings_repo
        )
        self._job_queue: JobQueueFacilitatorContract = job_queue
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._model_id: LlmModelId = (
            app_settings.llm_summary_model_id or app_settings.llm_model_id
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: QueuedJobInput) -> JobReport:
        conversation_id: ConversationId = decode_summary_payload(input_data.payload)
        if input_data.business_id is None:
            return NOTHING_DONE

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        conversation: ConversationDocument | None = self._conversation_repo.get(
            input_data.business_id, conversation_id
        )
        if (
            business is None
            or conversation is None
            or not self._may_remember(business, conversation)
        ):
            return NOTHING_DONE

        now: Microseconds = self._wall_clock.now_unix()
        if int(summary_due_at(conversation.last_message_at)) > int(now):
            self._job_queue.enqueue(
                SUMMARIZE_CONVERSATION_JOB,
                encode_summary_payload(conversation.id),
                business.id,
                run_at=summary_due_at(conversation.last_message_at),
            )
            return NOTHING_DONE

        if conversation.summarized_at is not None and int(
            conversation.summarized_at
        ) >= int(conversation.last_message_at):
            return NOTHING_DONE

        lines: list[tuple[MessageAuthor, str]] = transcript_lines(
            self._message_repo.list_by_conversation(business.id, conversation.id)
        )
        if not has_customer_words(lines):
            return NOTHING_DONE

        summary: ConversationSummaryText | None = self._summarize(
            business, lines, input_data
        )
        if summary is None or not self._may_remember(business, conversation):
            return NOTHING_DONE

        write = ConversationSummaryWrite(
            summary=summary,
            written_at=self._wall_clock.now_unix(),
            covers_until=conversation.last_message_at,
        )
        if (
            self._conversation_memory_repo.set_summary(
                business.id, conversation.id, write
            )
            is None
        ):
            return NOTHING_DONE

        return JobReport(processed_count=ProcessedItemCount(1))

    def _may_remember(
        self, business: BusinessDocument, conversation: ConversationDocument
    ) -> bool:
        """Memory is on, the conversation is real and its visitor not erased."""

        if conversation.is_sandbox or is_erased_conversation(conversation):
            return False

        if not view_assistant_settings(
            self._assistant_settings_repo.get_by_business(business.id)
        ).remembers_customers:
            return False

        contact: ContactDocument | None = self._contact_repo.get(
            business.id, conversation.contact_id
        )
        return contact is not None and contact.erased_at is None

    def _summarize(
        self,
        business: BusinessDocument,
        lines: list[tuple[MessageAuthor, str]],
        input_data: QueuedJobInput,
    ) -> ConversationSummaryText | None:
        try:
            return ask_for_summary(self._llm_adapter, self._model_id, business, lines)
        except ApplicationError as error:
            if not input_data.is_final_attempt:
                raise ExternalServiceError(
                    f"The conversation summary could not be written: {error}"
                ) from error

            LOGGER.warning(
                "A conversation summary of %s was given up: %s", business.id, error
            )
            return None
