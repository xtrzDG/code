"""Run one autotest scenario: a simulated customer, the assistant, the judge."""

from collections.abc import Sequence

from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AutotestScenarioResult,
    AutotestTranscriptLine,
)
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.assistants.autotest_runs import AutotestScenarioRun, JudgeVerdict
from app.schemas.dto.conversations import (
    AssistantReply,
    InboundMessage,
    LlmRequest,
    LlmResponse,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import AutotestCheckNote, SystemPromptText
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmProviderPayload,
    MessageText,
)
from app.use_cases.autotests.autotest_scenario_results import (
    build_scenario_result,
    sum_assistant_costs,
)
from app.utilities.assembly.autotest_evaluation import (
    check_conversation,
    decide_outcome,
)
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_OPENING_TEXT,
    JUDGE_SYSTEM_PROMPT,
    SILENT_ASSISTANT_TEXT,
    build_assistant_turn_text,
    build_customer_persona_prompt,
    build_judge_request_text,
    read_customer_message,
)
from app.utilities.assembly.judge_verdicts import parse_judge_verdict
from app.utilities.assembly.llm_costs import (
    DEFAULT_LLM_TOKEN_PRICES,
    estimate_llm_cost,
)


class RunAutotestScenarioUseCase(
    UseCaseContract[AutotestScenarioRun, AutotestScenarioResult]
):
    """
    Play one autotest scenario and judge it (concept section 11).

    The AI customer (a model with a persona prompt and no tools) writes up
    to `autotest_turn_limit` messages in the scenario language; each goes to
    the conversation engine as a sandbox owner-test message pinned to the
    version, with a channel user unique to the run and scenario. "[DONE]"
    ends the conversation early. The judge then scores the five criteria
    and deterministic checks look at what was actually created.

    Provider errors or an unreadable judge answer make the scenario
    ERRORED instead of failing the whole run. The cost is the assistant's
    stored message costs plus estimated customer and judge calls.
    """

    def __init__(
        self,
        conversation_turn_orchestrator: ConversationTurnOrchestratorContract,
        customer_llm_adapter: LlmAdapterContract,
        judge_llm_adapter: LlmAdapterContract,
        message_repo: MessageRepoContract,
        app_settings: AppSettings,
        llm_token_prices: Sequence[LlmTokenPrice] = DEFAULT_LLM_TOKEN_PRICES,
    ) -> None:
        self._conversation_turn_orchestrator: ConversationTurnOrchestratorContract = (
            conversation_turn_orchestrator
        )
        self._customer_llm_adapter: LlmAdapterContract = customer_llm_adapter
        self._judge_llm_adapter: LlmAdapterContract = judge_llm_adapter
        self._message_repo: MessageRepoContract = message_repo
        self._app_settings: AppSettings = app_settings
        self._llm_token_prices: tuple[LlmTokenPrice, ...] = tuple(llm_token_prices)

    def run(self, input_data: AutotestScenarioRun) -> AutotestScenarioResult:
        transcript: list[AutotestTranscriptLine] = []
        replies: list[AssistantReply] = []
        customer_costs: list[CostMicroUsd] = []
        conversation_error: ApplicationError | None = None
        try:
            self._converse(input_data, transcript, replies, customer_costs)
        except ApplicationError as error:
            conversation_error = error

        cost: int = sum(int(cost) for cost in customer_costs) + int(
            sum_assistant_costs(self._message_repo, input_data, replies)
        )
        if conversation_error is not None:
            return build_scenario_result(
                input_data,
                AutotestOutcome.ERRORED,
                transcript=transcript,
                check_notes=[
                    AutotestCheckNote(
                        f"The test conversation could not run: {conversation_error}"
                    )
                ],
                cost=CostMicroUsd(cost),
            )

        if not any(line.author is MessageAuthor.CUSTOMER for line in transcript):
            return build_scenario_result(
                input_data,
                AutotestOutcome.ERRORED,
                transcript=transcript,
                check_notes=[AutotestCheckNote("The AI customer wrote no message.")],
                cost=CostMicroUsd(cost),
            )

        check_notes: list[AutotestCheckNote] = check_conversation(
            input_data.scenario,
            replies,
        )
        try:
            judge_response: LlmResponse = self._judge_llm_adapter.complete(
                self._build_judge_request(input_data, transcript, replies)
            )
        except ApplicationError as error:
            return build_scenario_result(
                input_data,
                AutotestOutcome.ERRORED,
                transcript=transcript,
                check_notes=[
                    *check_notes,
                    AutotestCheckNote(f"The judge could not be asked: {error}"),
                ],
                cost=CostMicroUsd(cost),
            )

        cost += int(self._estimate_cost(judge_response))
        verdict: JudgeVerdict | None = parse_judge_verdict(
            str(judge_response.text) if judge_response.text is not None else None
        )
        if verdict is None:
            return build_scenario_result(
                input_data,
                AutotestOutcome.ERRORED,
                transcript=transcript,
                check_notes=[
                    *check_notes,
                    AutotestCheckNote("The judge's answer could not be read."),
                ],
                cost=CostMicroUsd(cost),
            )

        return build_scenario_result(
            input_data,
            decide_outcome(verdict.scores, check_notes),
            transcript=transcript,
            check_notes=check_notes,
            cost=CostMicroUsd(cost),
            verdict=verdict,
        )

    def _converse(
        self,
        scenario_run: AutotestScenarioRun,
        transcript: list[AutotestTranscriptLine],
        replies: list[AssistantReply],
        customer_costs: list[CostMicroUsd],
    ) -> None:
        """
        Fill `transcript`, `replies` and `customer_costs` as the conversation
        goes, so a provider error mid-way still leaves what happened so far.
        """

        persona_prompt: SystemPromptText = build_customer_persona_prompt(
            str(scenario_run.business.name),
            scenario_run.scenario,
            scenario_run.customer_phone_number,
            scenario_run.version.facts,
        )
        customer_transcript: list[LlmProviderPayload] = [
            self._customer_llm_adapter.build_user_text_turn(
                MessageText(CUSTOMER_OPENING_TEXT)
            )
        ]
        channel_user_id = ChannelUserId(
            f"autotest-{scenario_run.run_id}-{scenario_run.scenario.key}"
        )
        for _ in range(int(self._app_settings.autotest_turn_limit)):
            response: LlmResponse = self._customer_llm_adapter.complete(
                LlmRequest(
                    model_id=self._app_settings.llm_judge_model_id,
                    system_prompt=persona_prompt,
                    tools=[],
                    transcript=list(customer_transcript),
                    max_output_tokens=self._app_settings.llm_max_output_tokens,
                    effort=self._app_settings.llm_judge_effort,
                )
            )
            customer_costs.append(self._estimate_cost(response))
            customer_transcript.append(response.assistant_turn_payload)
            message: MessageText | None = read_customer_message(
                str(response.text) if response.text is not None else None
            )
            if message is None:
                break

            transcript.append(
                AutotestTranscriptLine(author=MessageAuthor.CUSTOMER, text=message)
            )
            reply: AssistantReply = self._conversation_turn_orchestrator.execute(
                InboundMessage(
                    business_id=scenario_run.business.id,
                    channel=ChannelKind.OWNER_TEST,
                    channel_user_id=channel_user_id,
                    text=message,
                    is_sandbox=True,
                    assistant_version_id=scenario_run.version.id,
                )
            )
            replies.append(reply)
            transcript.append(
                AutotestTranscriptLine(
                    author=MessageAuthor.ASSISTANT,
                    text=reply.text,
                )
                if reply.text is not None
                else AutotestTranscriptLine(
                    author=MessageAuthor.SYSTEM,
                    text=MessageText(SILENT_ASSISTANT_TEXT),
                )
            )
            customer_transcript.append(
                self._customer_llm_adapter.build_user_text_turn(
                    build_assistant_turn_text(reply)
                )
            )

    def _build_judge_request(
        self,
        scenario_run: AutotestScenarioRun,
        transcript: list[AutotestTranscriptLine],
        replies: list[AssistantReply],
    ) -> LlmRequest:
        return LlmRequest(
            model_id=self._app_settings.llm_judge_model_id,
            system_prompt=SystemPromptText(JUDGE_SYSTEM_PROMPT),
            tools=[],
            transcript=[
                self._judge_llm_adapter.build_user_text_turn(
                    build_judge_request_text(
                        scenario_run.scenario,
                        scenario_run.version.facts,
                        transcript,
                        replies,
                        scenario_run.business.owner_language,
                    )
                )
            ],
            max_output_tokens=self._app_settings.llm_max_output_tokens,
            effort=self._app_settings.llm_judge_effort,
        )

    def _estimate_cost(self, response: LlmResponse) -> CostMicroUsd:
        return estimate_llm_cost(
            self._llm_token_prices,
            self._app_settings.llm_judge_model_id,
            response.input_tokens,
            response.output_tokens,
        )
