"""The judge of one real conversation: its request, the call and the score."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.llm import LlmAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversation_quality import ConversationQualityScoreDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.assistants.autotest_runs import JudgeVerdict
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.quality import QualityJudgement, QualityJudgeRequest
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import JudgeNote, SystemPromptText
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.assembly.judge_verdicts import parse_judge_verdict
from app.utilities.legal.processor_coverage import quality_judge_model_id
from app.utilities.quality.quality_costs import cost_of, price_of, worst_case_cost
from app.utilities.quality.quality_prompts import (
    QUALITY_JUDGE_SYSTEM_PROMPT,
    blank_contacts,
    build_quality_request_text,
)
from app.utilities.quality.quality_sampling import quality_score_id_of, to_hundredths


class ConversationQualityJudge:
    """
    Scores one real conversation with the quality judge: the assistant's
    own model while QUALITY_SAMPLING_JUDGE_SAME_PROVIDER is on (the
    default), else LLM_JUDGE_MODEL_ID (the other provider's, once the
    sub-processor list covers it): the five autotest criteria on its
    transcript with contacts blanked out, notes in the owner's language
    with contacts blanked out again. Provider errors propagate (the caller
    skips the conversation); an unreadable answer gives no score but its
    cost.
    """

    def __init__(
        self,
        llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
        llm_token_prices: Sequence[LlmTokenPrice],
    ) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._app_settings: AppSettings = app_settings
        self._model_id: LlmModelId = quality_judge_model_id(app_settings)
        self._price: LlmTokenPrice = price_of(llm_token_prices, self._model_id)

    def prepare(
        self,
        business: BusinessDocument,
        facts: Sequence[BusinessFact],
        messages: Sequence[MessageDocument],
    ) -> QualityJudgeRequest:
        """The request and the most it may cost."""

        text: MessageText = build_quality_request_text(
            facts, messages, business.country_code, business.owner_language
        )
        return QualityJudgeRequest(
            request=LlmRequest(
                model_id=self._model_id,
                system_prompt=SystemPromptText(QUALITY_JUDGE_SYSTEM_PROMPT),
                tools=[],
                transcript=[self._llm_adapter.build_user_text_turn(text)],
                max_output_tokens=self._app_settings.llm_max_output_tokens,
                effort=self._app_settings.llm_judge_effort,
            ),
            worst_case_cost=worst_case_cost(
                self._price,
                f"{QUALITY_JUDGE_SYSTEM_PROMPT}\n{text}",
                self._app_settings.llm_max_output_tokens,
            ),
        )

    def judge(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        prepared: QualityJudgeRequest,
        now: Microseconds,
    ) -> QualityJudgement:
        response: LlmResponse = self._llm_adapter.complete(prepared.request)
        cost: CostMicroUsd = cost_of(
            self._price, response.input_tokens, response.output_tokens
        )
        verdict: JudgeVerdict | None = parse_judge_verdict(
            str(response.text) if response.text is not None else None
        )
        if verdict is None or not verdict.scores:
            return QualityJudgement(cost_micro_usd=cost)

        return QualityJudgement(
            score=ConversationQualityScoreDocument(
                id=quality_score_id_of(conversation.id),
                business_id=business.id,
                conversation_id=conversation.id,
                assistant_version_id=conversation.assistant_version_id,
                channel=conversation.channel,
                language=conversation.language,
                scores=list(verdict.scores),
                score_hundredths=to_hundredths(verdict.scores),
                judge_notes=[
                    JudgeNote(blank_contacts(str(note), business.country_code))
                    for note in verdict.notes
                ],
                judge_model_id=self._model_id,
                cost_micro_usd=cost,
                judged_at=now,
                created_at=now,
                updated_at=now,
            ),
            cost_micro_usd=cost,
        )
