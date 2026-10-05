"""Scripted models of the assembly testbed: the AI customer, the judge and fakes."""

import json
import re
from collections.abc import Mapping

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.dto.conversations import AssistantReply, InboundMessage, LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.billing.constrained_integers import CostMicroUsd
from app.schemas.typings.conversations.strings import MessageText
from tests.assembly.assembly_store import AssemblyStore
from tests.assembly.autotest_scripts import (
    PERFECT_SCORES,
    SCENARIO_LINE_PATTERN,
    CustomerScript,
    ReplyScript,
    default_customer_script,
    default_reply_script,
    price_reply,
    read_scenario_key,
    read_scenario_kind,
)
from tests.assembly.fake_engine_and_voice import (
    FakeAssistantToolCatalog,
    FakeAuthenticationOperator,
    FakeCallGreetingUseCase,
    FakeConversationTurnOrchestrator,
    FakeVoiceAgentProvisioner,
)
from tests.assembly.llm_request_helpers import (
    TokenReportingLlmAdapter,
    count_assistant_turns,
    read_last_user_text,
)


class AssemblyScriptedModels(AssemblyStore):
    """The store with the scripted customer, judge, conversation and voice fakes."""

    def __init__(
        self,
        environment: Mapping[str, str] | None = None,
        customer_token_usage: tuple[int, int] | None = None,
        judge_token_usage: tuple[int, int] | None = None,
        reply_cost: int = 0,
    ) -> None:
        super().__init__(environment)
        self.customer_script: CustomerScript = default_customer_script
        self.reply_scripts: dict[str, ReplyScript] = {}
        self.judge_scores: dict[str, dict[str, int]] = {}
        self.judge_raw_answers: dict[str, str] = {}
        self.judge_errors: set[str] = set()
        self.conversation = FakeConversationTurnOrchestrator(
            self._reply,
            self.message_repo,
            CostMicroUsd(reply_cost),
        )
        self.customer_requests = ScriptedLlmAdapter(self._customer_turn)
        self.judge_requests = ScriptedLlmAdapter(self._judge_turn)
        self.customer_llm: LlmAdapterContract = (
            TokenReportingLlmAdapter(self.customer_requests, *customer_token_usage)
            if customer_token_usage is not None
            else self.customer_requests
        )
        self.judge_llm: LlmAdapterContract = (
            TokenReportingLlmAdapter(self.judge_requests, *judge_token_usage)
            if judge_token_usage is not None
            else self.judge_requests
        )
        self.voice_provisioner = FakeVoiceAgentProvisioner()
        self.call_greeting = FakeCallGreetingUseCase()
        self.tool_catalog = FakeAssistantToolCatalog()
        self.authentication = FakeAuthenticationOperator()

    def _customer_turn(self, request: LlmRequest) -> ScriptedLlmTurn:
        return ScriptedLlmTurn(
            text=MessageText(
                self.customer_script(request, count_assistant_turns(request))
            )
        )

    def _judge_turn(self, request: LlmRequest) -> ScriptedLlmTurn:
        match: re.Match[str] | None = SCENARIO_LINE_PATTERN.search(
            read_last_user_text(request)
        )
        assert match is not None
        scenario_key: str = match.group(1)
        if scenario_key in self.judge_errors:
            raise ExternalServiceError("Judge model is unavailable.")

        raw_answer: str | None = self.judge_raw_answers.get(scenario_key)
        if raw_answer is None:
            raw_answer = json.dumps(
                {
                    "scores": self.judge_scores.get(scenario_key, PERFECT_SCORES),
                    "notes": [f"Judged {scenario_key}."],
                }
            )

        return ScriptedLlmTurn(text=MessageText(raw_answer))

    def _reply(self, message: InboundMessage, turn_index: int) -> AssistantReply:
        scenario_key: str = read_scenario_key(message)
        script: ReplyScript | None = self.reply_scripts.get(scenario_key)
        if script is not None:
            return script(message, scenario_key, turn_index)

        if read_scenario_kind(scenario_key) is AutotestScenarioKind.PRICE_QUESTION:
            # The scripted assistant names every price of the price list, so
            # each price question finds its item's price.
            business = self.business_repo.get(message.business_id)
            assert business is not None
            return price_reply(
                scenario_key,
                self.knowledge_repo.list_by_business(message.business_id),
                str(business.currency_code),
            )

        return default_reply_script(message, scenario_key, turn_index)
