"""Run one autotest scenario: a simulated customer, the assistant, the judge."""

from collections.abc import Sequence

from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestCheckCode, AutotestOutcome
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import (
    AutotestScenarioResult,
    AutotestTranscriptLine,
)
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    AutotestScenarioRun,
    JudgeVerdict,
    OwnerCheckSpec,
)
from app.schemas.dto.conversations import (
    AssistantReply,
    LlmRequest,
    LlmResponse,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.use_cases.autotests.autotest_scenario_results import (
    build_scenario_result,
    sum_assistant_costs,
)
from app.use_cases.autotests.scenario_conversation import ScenarioConversation
from app.utilities.assembly.autotest_evaluation import (
    check_conversation,
    check_failure,
    decide_outcome,
)
from app.utilities.assembly.autotest_prompts import (
    JUDGE_SYSTEM_PROMPT,
    build_judge_request_text,
)
from app.utilities.assembly.judge_verdicts import parse_judge_verdict
from app.utilities.assembly.llm_costs import (
    DEFAULT_LLM_TOKEN_PRICES,
    estimate_llm_cost,
)
from app.utilities.assembly.owner_check_evaluation import check_owner_expectation


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
    and deterministic checks look at what was actually created. An owner
    check opens with its question as written and is decided by its
    expectation alone (`ScenarioConversation`, `check_owner_expectation`).

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
        conversation = ScenarioConversation(
            self._conversation_turn_orchestrator,
            self._customer_llm_adapter,
            self._app_settings,
            self._estimate_cost,
        )
        conversation_error: ApplicationError | None = None
        try:
            conversation.play(input_data)
        except ApplicationError as error:
            conversation_error = error

        transcript: list[AutotestTranscriptLine] = conversation.transcript
        replies: list[AssistantReply] = conversation.replies
        cost: int = sum(int(cost) for cost in conversation.customer_costs) + int(
            sum_assistant_costs(self._message_repo, input_data, replies)
        )
        if conversation_error is not None:
            return build_scenario_result(
                input_data,
                AutotestOutcome.ERRORED,
                transcript=transcript,
                check_failures=[
                    check_failure(
                        AutotestCheckCode.CONVERSATION_FAILED,
                        f"The test conversation could not run: {conversation_error}",
                    )
                ],
                cost=CostMicroUsd(cost),
            )

        if not any(line.author is MessageAuthor.CUSTOMER for line in transcript):
            return build_scenario_result(
                input_data,
                AutotestOutcome.ERRORED,
                transcript=transcript,
                check_failures=[
                    check_failure(
                        AutotestCheckCode.NO_CUSTOMER_MESSAGE,
                        "The AI customer wrote no message.",
                    )
                ],
                cost=CostMicroUsd(cost),
            )

        check_failures: list[AutotestCheckFailure] = check_conversation(
            input_data.scenario,
            replies,
            str(input_data.business.name),
        )
        owner_check: OwnerCheckSpec | None = input_data.scenario.owner_check
        if owner_check is not None:
            # The owner's own check is decided by its expectation, not judged.
            check_failures.extend(check_owner_expectation(owner_check, replies))
            return build_scenario_result(
                input_data,
                AutotestOutcome.FAILED if check_failures else AutotestOutcome.PASSED,
                transcript=transcript,
                check_failures=check_failures,
                cost=CostMicroUsd(cost),
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
                check_failures=[
                    *check_failures,
                    check_failure(
                        AutotestCheckCode.JUDGE_UNAVAILABLE,
                        f"The judge could not be asked: {error}",
                    ),
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
                check_failures=[
                    *check_failures,
                    check_failure(
                        AutotestCheckCode.JUDGE_UNREADABLE,
                        "The judge's answer could not be read.",
                    ),
                ],
                cost=CostMicroUsd(cost),
            )

        return build_scenario_result(
            input_data,
            decide_outcome(
                verdict.scores, [failure.note for failure in check_failures]
            ),
            transcript=transcript,
            check_failures=check_failures,
            cost=CostMicroUsd(cost),
            verdict=verdict,
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
