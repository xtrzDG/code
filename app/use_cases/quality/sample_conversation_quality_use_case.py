"""Periodic job: the judge scores a small, cost-capped sample of real conversations."""

import logging
from collections.abc import Sequence
from datetime import timedelta

from typed_time_provider import Microseconds, WallClock

from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.repositories.quality_repositories import (
    ConversationQualityRepoContract,
    QualitySampleInputRepoContract,
    QualityTotalsRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.quality_settings import QualitySettings
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.jobs import JobReport, JobTick
from app.schemas.dto.platform_health import ActivityWindow
from app.schemas.dto.quality import QualityJudgement, QualityJudgeRequest
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.quality.conversation_quality_judge import ConversationQualityJudge
from app.utilities.assembly.llm_costs import DEFAULT_LLM_TOKEN_PRICES
from app.utilities.quality.quality_sampling import (
    budget_micro_usd,
    is_sampled,
    take_turns,
    utc_day_start,
)

logger: logging.Logger = logging.getLogger(__name__)

SAMPLED_STATUSES: frozenset[BusinessStatus] = frozenset(
    {BusinessStatus.LIVE, BusinessStatus.PAUSED}
)
MICROSECONDS_PER_HOUR: int = int(timedelta(hours=1).total_seconds()) * 1_000_000
# Conversations whose last message is 1 to 48 hours old: quiet for an hour
# (most likely over), and a run late by a day still sees them.
QUIET_FOR: int = MICROSECONDS_PER_HOUR
LOOK_BACK: int = 48 * MICROSECONDS_PER_HOUR
KEPT_FOR: int = 90 * 24 * MICROSECONDS_PER_HOUR
MAX_CANDIDATES: DocumentQueryLimit = DocumentQueryLimit(2_000)

type Candidate = tuple[BusinessDocument, ConversationDocument]


class SampleConversationQualityUseCase(UseCaseContract[JobTick, JobReport]):
    """
    The nightly `sample_conversation_quality` job (production quality):
    across live and paused businesses, the conversations of the last two
    days that have been quiet for an hour, sandbox left out, are sampled
    (QUALITY_SAMPLE_PERCENT, a stable hash of each id), at most
    QUALITY_SAMPLE_PER_BUSINESS per business, never one judged before.
    Businesses take turns, and before each call its worst case (every
    output token) is checked against what is left of the UTC day's
    QUALITY_SAMPLE_BUDGET_CENTS: the night stops at the cap. A failing
    call skips its conversation. Scores older than 90 days are deleted.
    The report counts the conversations scored.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        sample_input_repo: QualitySampleInputRepoContract,
        message_repo: MessageRepoContract,
        assistant_version_repo: AssistantVersionRepoContract,
        conversation_quality_repo: ConversationQualityRepoContract,
        quality_totals_repo: QualityTotalsRepoContract,
        llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        llm_token_prices: Sequence[LlmTokenPrice] = DEFAULT_LLM_TOKEN_PRICES,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._input_repo: QualitySampleInputRepoContract = sample_input_repo
        self._message_repo: MessageRepoContract = message_repo
        self._version_repo: AssistantVersionRepoContract = assistant_version_repo
        self._quality_repo: ConversationQualityRepoContract = conversation_quality_repo
        self._totals_repo: QualityTotalsRepoContract = quality_totals_repo
        self._settings: QualitySettings = app_settings.quality
        self._judge: ConversationQualityJudge = ConversationQualityJudge(
            llm_adapter, app_settings, llm_token_prices
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobTick) -> JobReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        self._totals_repo.delete_judged_before(Microseconds(int(now) - KEPT_FOR))
        budget: int = budget_micro_usd(self._settings.sample_budget_cents)
        if int(self._settings.sample_percent) == 0 or budget == 0:
            return JobReport()

        spent: int = int(
            self._totals_repo.sum_judged(
                ActivityWindow(
                    since=utc_day_start(now), until=Microseconds(int(now) + 1)
                )
            ).cost_micro_usd
        )
        scored: int = 0
        for business, conversation in take_turns(self._sample_by_business(now)):
            messages: list[MessageDocument] = self._message_repo.list_by_conversation(
                business.id, conversation.id
            )
            if not is_judgeable(messages):
                continue

            version: AssistantVersionDocument | None = self._version_repo.get(
                business.id, conversation.assistant_version_id
            )
            prepared: QualityJudgeRequest = self._judge.prepare(
                business, [] if version is None else version.facts, messages
            )
            if spent + int(prepared.worst_case_cost) > budget:
                logger.info(
                    "Quality sampling stopped at its budget: %d of %d micro-USD.",
                    spent,
                    budget,
                )
                break

            try:
                judged: QualityJudgement = self._judge.judge(
                    business, conversation, prepared, now
                )
            except ApplicationError as error:
                logger.warning("Quality judge of %s failed: %s", conversation.id, error)
                continue

            spent += int(judged.cost_micro_usd)
            if judged.score is not None:
                self._quality_repo.save(judged.score)
                scored += 1

        return JobReport(processed_count=ProcessedItemCount(scored))

    def _sample_by_business(self, now: Microseconds) -> list[list[Candidate]]:
        window = ActivityWindow(
            since=Microseconds(int(now) - LOOK_BACK),
            until=Microseconds(int(now) - QUIET_FOR),
        )
        groups: list[list[Candidate]] = []
        for business in self._business_repo.list_all():
            if business.status not in SAMPLED_STATUSES:
                continue

            picked: list[Candidate] = []
            for conversation in self._input_repo.list_recent(
                business.id, window, MAX_CANDIDATES
            ):
                if len(picked) >= int(self._settings.sample_per_business):
                    break

                if (
                    is_sampled(conversation.id, self._settings.sample_percent)
                    and self._quality_repo.get(business.id, conversation.id) is None
                ):
                    picked.append((business, conversation))

            groups.append(picked)

        return groups


def is_judgeable(messages: Sequence[MessageDocument]) -> bool:
    """The customer wrote and the assistant answered at least once."""

    authors: set[MessageAuthor] = {message.author for message in messages}
    return MessageAuthor.CUSTOMER in authors and MessageAuthor.ASSISTANT in authors
