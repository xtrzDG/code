"""Production quality over the value test world: conversations, a judge, the job."""

import json
from collections.abc import Callable

from typed_time_provider import Microseconds

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.assistant_repositories import AssistantVersionRepository
from app.repositories.quality_repositories import (
    ConversationQualityRepository,
    QualitySampleInputRepository,
    QualityTotalsRepository,
)
from app.repositories.retention_settings_repositories import (
    BusinessPrivacySettingsRepository,
)
from app.schemas.configurations.quality_settings import QualitySettings
from app.schemas.constants.assistants import JudgeCriterion
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.jobs import JobTick
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.quality.constrained_integers import (
    QualitySampleBudgetCents,
    QualitySampleBusinessLimit,
    QualitySamplePercent,
)
from app.use_cases.quality.sample_conversation_quality_use_case import (
    SampleConversationQualityUseCase,
)
from tests.value.value_world import ValueWorld

# The judge's list price in the tests: 0.1 micro-dollar an input token,
# 1 an output token, so its worst case is about LLM_MAX_OUTPUT_TOKENS.
JUDGE_PRICES: tuple[LlmTokenPrice, ...] = (
    LlmTokenPrice(
        model_id=LlmModelId("gpt-5-mini"),
        input_price=LlmPricePerMillionTokensMicroUsd(100_000),
        output_price=LlmPricePerMillionTokensMicroUsd(1_000_000),
    ),
)


def verdict(notes: list[str] | None = None, **scores: int) -> str:
    values = {criterion.value: 5 for criterion in JudgeCriterion} | scores
    return json.dumps({"scores": values, "notes": notes or []})


def tick(bench: QualityBench) -> JobTick:
    return JobTick(
        job_name=JobName("sample_conversation_quality"), scheduled_at=bench.now()
    )


class CountingJudge(ScriptedLlmAdapter):
    """A scripted judge whose answers report the tokens they used."""

    def __init__(
        self,
        answer: Callable[[LlmRequest], str] = lambda request: verdict(),
        input_tokens: int = 2_000,
        output_tokens: int = 10_000,
    ) -> None:
        super().__init__(
            lambda request: ScriptedLlmTurn(text=MessageText(answer(request)))
        )
        self._usage: dict[str, LlmTokenCount] = {
            "input_tokens": LlmTokenCount(input_tokens),
            "output_tokens": LlmTokenCount(output_tokens),
        }

    def complete(self, request: LlmRequest) -> LlmResponse:
        return super().complete(request).model_copy(update=self._usage)


class QualityBench:
    """One in-memory platform with the quality repositories and job."""

    def __init__(self) -> None:
        self.world = ValueWorld()
        self.scores = InMemoryDocumentCollectionAdapter[
            ConversationQualityScoreDocument
        ](ConversationQualityScoreDocument)
        self.quality_repo = ConversationQualityRepository(self.scores)
        self.totals_repo = QualityTotalsRepository(self.scores)
        self.version_repo = AssistantVersionRepository(
            InMemoryDocumentCollectionAdapter[AssistantVersionDocument](
                AssistantVersionDocument
            )
        )
        self.privacy_settings_repo = BusinessPrivacySettingsRepository(
            InMemoryDocumentCollectionAdapter[BusinessPrivacySettingsDocument](
                BusinessPrivacySettingsDocument
            )
        )

    def now(self) -> Microseconds:
        return self.world.clock.now_microseconds()

    def live_business(
        self, status: BusinessStatus = BusinessStatus.LIVE
    ) -> BusinessDocument:
        business = self.world.add_business()
        business.status = status
        self.world.business_repo.save(business)
        return business

    def conversation(
        self,
        business: BusinessDocument,
        hours_ago: float = 3,
        texts: tuple[str, ...] = ("Do you have a table for two?", "Yes, at 19:00."),
        is_sandbox: bool = False,
    ) -> ConversationDocument:
        """A conversation whose last message is `hours_ago` old."""

        contact = self.world.add_contact(business)
        conversation = self.world.add_conversation(
            business, contact, is_sandbox=is_sandbox
        )
        moment = Microseconds(int(self.now()) - int(hours_ago * 3_600_000_000))
        conversation.last_message_at = moment
        self.world.conversation_repo.save(conversation)
        for index, text in enumerate(texts):
            is_customer: bool = index % 2 == 0
            self.world.message_repo.save(
                MessageDocument(
                    conversation_id=conversation.id,
                    business_id=business.id,
                    direction=(
                        MessageDirection.INBOUND
                        if is_customer
                        else MessageDirection.OUTBOUND
                    ),
                    author=(
                        MessageAuthor.CUSTOMER
                        if is_customer
                        else MessageAuthor.ASSISTANT
                    ),
                    text=MessageText(text),
                    created_at=Microseconds(int(moment) - (len(texts) - index)),
                    updated_at=moment,
                )
            )

        return conversation

    def job(
        self,
        judge: ScriptedLlmAdapter,
        percent: int = 100,
        per_business: int = 20,
        budget_cents: int = 500,
        judge_same_provider: bool = True,
    ) -> SampleConversationQualityUseCase:
        settings = self.world.settings.model_copy(
            update={
                "quality": QualitySettings(
                    sample_percent=QualitySamplePercent(percent),
                    sample_per_business=QualitySampleBusinessLimit(per_business),
                    sample_budget_cents=QualitySampleBudgetCents(budget_cents),
                    judge_same_provider=judge_same_provider,
                )
            }
        )
        return SampleConversationQualityUseCase(
            business_repo=self.world.business_repo,
            sample_input_repo=QualitySampleInputRepository(
                self.world.conversation_collection
            ),
            message_repo=self.world.message_repo,
            assistant_version_repo=self.version_repo,
            conversation_quality_repo=self.quality_repo,
            quality_totals_repo=self.totals_repo,
            privacy_settings_repo=self.privacy_settings_repo,
            llm_adapter=judge,
            app_settings=settings,
            wall_clock=self.world.clock.wall_clock,
            llm_token_prices=JUDGE_PRICES,
        )

    def stored_scores(self) -> list[ConversationQualityScoreDocument]:
        return self.scores.list_all()
