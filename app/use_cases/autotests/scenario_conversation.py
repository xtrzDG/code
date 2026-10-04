"""
The test conversation of one autotest scenario: the AI customer writes,
the conversation engine answers as the version under test. An owner check
opens with its question word for word and goes on with the AI customer
only when its answer must lead to a request.
"""

from collections.abc import Callable

from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.llm import LlmAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestExpectation
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.assistants import AutotestTranscriptLine
from app.schemas.dto.assistants.autotest_runs import AutotestScenarioRun, OwnerCheckSpec
from app.schemas.dto.conversations import (
    AssistantReply,
    InboundMessage,
    LlmRequest,
    LlmResponse,
)
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import (
    ChannelUserId,
    LlmProviderPayload,
    MessageText,
)
from app.utilities.assembly.autotest_prompts import (
    CUSTOMER_OPENING_TEXT,
    SILENT_ASSISTANT_TEXT,
    build_assistant_turn_text,
    build_customer_persona_prompt,
    build_owner_check_continuation,
    read_customer_message,
)


class ScenarioConversation:
    """
    Plays one scenario's conversation, filling the transcript, the replies
    and the AI customer's costs as it goes, so a provider error mid-way
    still leaves what happened so far.
    """

    def __init__(
        self,
        conversation_turn_orchestrator: ConversationTurnOrchestratorContract,
        customer_llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
        estimate_cost: Callable[[LlmResponse], CostMicroUsd],
    ) -> None:
        self._orchestrator: ConversationTurnOrchestratorContract = (
            conversation_turn_orchestrator
        )
        self._customer: LlmAdapterContract = customer_llm_adapter
        self._settings: AppSettings = app_settings
        self._estimate_cost: Callable[[LlmResponse], CostMicroUsd] = estimate_cost
        self.transcript: list[AutotestTranscriptLine] = []
        self.replies: list[AssistantReply] = []
        self.customer_costs: list[CostMicroUsd] = []

    def play(self, scenario_run: AutotestScenarioRun) -> None:
        turn_limit: int = int(self._settings.autotest_turn_limit)
        owner_check: OwnerCheckSpec | None = scenario_run.scenario.owner_check
        if owner_check is None:
            customer_transcript: list[LlmProviderPayload] = [
                self._customer.build_user_text_turn(MessageText(CUSTOMER_OPENING_TEXT))
            ]
        else:
            reply: AssistantReply = self._exchange(
                scenario_run, MessageText(str(owner_check.question))
            )
            if owner_check.expectation is not AutotestExpectation.MUST_CREATE_LEAD:
                return

            customer_transcript = [
                self._customer.build_user_text_turn(
                    build_owner_check_continuation(str(owner_check.question), reply)
                )
            ]
            turn_limit -= 1

        persona_prompt: SystemPromptText = build_customer_persona_prompt(
            str(scenario_run.business.name),
            scenario_run.scenario,
            scenario_run.customer_phone_number,
            scenario_run.version.facts,
        )
        for _ in range(turn_limit):
            response: LlmResponse = self._customer.complete(
                LlmRequest(
                    model_id=self._settings.llm_judge_model_id,
                    system_prompt=persona_prompt,
                    tools=[],
                    transcript=list(customer_transcript),
                    max_output_tokens=self._settings.llm_max_output_tokens,
                    effort=self._settings.llm_judge_effort,
                )
            )
            self.customer_costs.append(self._estimate_cost(response))
            customer_transcript.append(response.assistant_turn_payload)
            message: MessageText | None = read_customer_message(
                str(response.text) if response.text is not None else None
            )
            if message is None:
                break

            reply = self._exchange(scenario_run, message)
            customer_transcript.append(
                self._customer.build_user_text_turn(build_assistant_turn_text(reply))
            )

    def _exchange(
        self, scenario_run: AutotestScenarioRun, message: MessageText
    ) -> AssistantReply:
        """One customer message to the version under test and its reply."""

        self.transcript.append(
            AutotestTranscriptLine(author=MessageAuthor.CUSTOMER, text=message)
        )
        reply: AssistantReply = self._orchestrator.execute(
            InboundMessage(
                business_id=scenario_run.business.id,
                channel=ChannelKind.OWNER_TEST,
                channel_user_id=ChannelUserId(
                    f"autotest-{scenario_run.run_id}-{scenario_run.scenario.key}"
                ),
                text=message,
                is_sandbox=True,
                assistant_version_id=scenario_run.version.id,
            )
        )
        self.replies.append(reply)
        self.transcript.append(
            AutotestTranscriptLine(author=MessageAuthor.ASSISTANT, text=reply.text)
            if reply.text is not None
            else AutotestTranscriptLine(
                author=MessageAuthor.SYSTEM, text=MessageText(SILENT_ASSISTANT_TEXT)
            )
        )
        return reply
