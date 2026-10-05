"""Periodic job: what customers ask about, grouped once a night per business."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.booking_repositories import (
    UnansweredQuestionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.topic_repositories import (
    ConversationTopicsRepoContract,
    TopicInputRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_topics import (
    ConversationTopicsDocument,
    TopicLanguageGroup,
)
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import UnansweredQuestionDocument
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.platform.constrained_integers import (
    KeysetReadLimit,
    ProcessedItemCount,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.insights.topics.topic_grouper import TopicGrouper
from app.use_cases.shared.business_walk import walk_businesses
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)
from app.utilities.value.topic_batches import (
    FirstMessage,
    language_batches,
    previous_labels,
    to_group,
)
from app.utilities.value.topic_grouping import GroupedTopic
from app.utilities.value.value_keys import conversation_topics_id_of

logger: logging.Logger = logging.getLogger(__name__)

GROUPED_STATUSES: frozenset[BusinessStatus] = frozenset(
    {BusinessStatus.LIVE, BusinessStatus.PAUSED}
)
WINDOW_MICROSECONDS: int = int(timedelta(days=30).total_seconds()) * 1_000_000
# The local night hours a business's topics are grouped in (retried each
# hour of them after a failure).
FIRST_HOUR: int = 3
LAST_HOUR: int = 9
MAX_CONVERSATIONS: DocumentQueryLimit = DocumentQueryLimit(200)
MAX_QUESTIONS: KeysetReadLimit = KeysetReadLimit(100)


class GroupConversationTopicsUseCase(UseCaseContract[JobTick, JobReport]):
    """
    Hourly job over live and paused businesses: in the local night (03:00
    to 09:00), once a day, the first messages of the last 30 days'
    conversations (the newest 200, sandbox left out) and the open questions
    the assistant could not answer (the 100 most asked) are grouped by a
    cheap model into at most 12 labelled topics per customer language, and
    stored as the business's one topics document. A business never grouped
    is grouped at once. No conversation and no question: an empty document,
    no model call. A failed language keeps the stored topics and is tried
    again the next hour; one failing business never stops the others.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        conversation_topics_repo: ConversationTopicsRepoContract,
        topic_input_repo: TopicInputRepoContract,
        unanswered_question_repo: UnansweredQuestionRepoContract,
        llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._topics_repo: ConversationTopicsRepoContract = conversation_topics_repo
        self._input_repo: TopicInputRepoContract = topic_input_repo
        self._question_repo: UnansweredQuestionRepoContract = unanswered_question_repo
        self._grouper: TopicGrouper = TopicGrouper(llm_adapter, app_settings)
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        grouped: int = 0
        for business in walk_businesses(self._business_repo):
            if business.status not in GROUPED_STATUSES:
                continue

            try:
                grouped += int(self._group_if_due(business))
            except Exception:
                logger.exception("Topics of business %s failed.", business.id)

        return JobReport(processed_count=ProcessedItemCount(grouped))

    def _group_if_due(self, business: BusinessDocument) -> bool:
        now: Microseconds = self._wall_clock.now_unix()
        stored: ConversationTopicsDocument | None = self._topics_repo.get(business.id)
        if not is_grouping_due(business, stored, now):
            return False

        start: Microseconds = Microseconds(int(now) - WINDOW_MICROSECONDS)
        earlier: list[TopicLanguageGroup] = [] if stored is None else stored.groups
        groups: list[TopicLanguageGroup] = []
        for batch in language_batches(
            self._first_messages(business, start, now), self._open_questions(business)
        ):
            topics: list[GroupedTopic] | None = self._grouper.group(
                business, batch, previous_labels(earlier, batch.language)
            )
            if topics is None:
                return False

            groups.append(to_group(batch, topics))

        self._topics_repo.save(
            ConversationTopicsDocument(
                id=conversation_topics_id_of(business.id),
                business_id=business.id,
                label_language=business.owner_language,
                window_from=start,
                window_to=now,
                groups=groups,
                created_at=now if stored is None else stored.created_at,
                updated_at=now,
            )
        )
        return True

    def _first_messages(
        self,
        business: BusinessDocument,
        start: Microseconds,
        end: Microseconds,
    ) -> list[FirstMessage]:
        """Oldest conversation first, so the items keep their order each night."""

        conversations: list[ConversationDocument] = self._input_repo.list_started(
            business.id, start, end, MAX_CONVERSATIONS
        )
        firsts: list[FirstMessage] = []
        for conversation in reversed(conversations):
            message: MessageDocument | None = (
                self._input_repo.find_first_customer_message(
                    business.id, conversation.id
                )
            )
            if message is not None and str(message.text).strip():
                firsts.append(FirstMessage(conversation.language, str(message.text)))

        return firsts

    def _open_questions(
        self, business: BusinessDocument
    ) -> list[UnansweredQuestionDocument]:
        return self._question_repo.page_by_rank(
            business.id, KeysetSlice(limit=MAX_QUESTIONS), False, False
        )


def is_grouping_due(
    business: BusinessDocument,
    stored: ConversationTopicsDocument | None,
    now: Microseconds,
) -> bool:
    """Never grouped; else in the local night, not grouped yet that day."""

    if stored is None:
        return True

    zone: ZoneInfo = load_time_zone(business.timezone)
    local_now: datetime = to_local_moment(microseconds_to_seconds(int(now)), zone)
    if not FIRST_HOUR <= local_now.hour < LAST_HOUR:
        return False

    grouped_on: datetime = to_local_moment(
        microseconds_to_seconds(int(stored.window_to)), zone
    )
    return grouped_on.date() < local_now.date()
