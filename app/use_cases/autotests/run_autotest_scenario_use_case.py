"""Run one autotest scenario: every play it needs, merged into one result."""

from collections.abc import Sequence

from app.contracts.conversation_flow import ConversationTurnOrchestratorContract
from app.contracts.llm import LlmAdapterContract
from app.contracts.repositories.conversation_repositories import MessageRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import AutotestOutcome
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.assembly_sources import LlmTokenPrice
from app.schemas.dto.assistants.autotest_runs import AutotestScenarioRun
from app.use_cases.autotests.scenario_sample_player import ScenarioSamplePlayer
from app.utilities.assembly.autotest_samples import merge_sample_results
from app.utilities.assembly.llm_costs import DEFAULT_LLM_TOKEN_PRICES


class RunAutotestScenarioUseCase(
    UseCaseContract[AutotestScenarioRun, AutotestScenarioResult]
):
    """
    Play one autotest scenario and judge it (concept section 11; see
    `ScenarioSamplePlayer` for one play). A launch-critical scenario is
    played `sample_count` times, each with a customer of its own, and
    passes only when every play passed (pass^k): the plays stop at the
    first one that did not pass, since the scenario has failed then.
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
        self._player: ScenarioSamplePlayer = ScenarioSamplePlayer(
            conversation_turn_orchestrator,
            customer_llm_adapter,
            judge_llm_adapter,
            message_repo,
            app_settings,
            llm_token_prices,
        )

    def run(self, input_data: AutotestScenarioRun) -> AutotestScenarioResult:
        plays: list[AutotestScenarioResult] = []
        for sample_number in range(1, int(input_data.scenario.sample_count) + 1):
            plays.append(self._player.play(input_data, sample_number))
            if plays[-1].outcome is not AutotestOutcome.PASSED:
                break

        return merge_sample_results(plays, input_data.scenario.sample_count)
