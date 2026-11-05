"""The voice checks of an autotest run: simulated calls in each language."""

import logging
from datetime import datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.use_case_contract import UseCaseContract
from app.contracts.voice_platform import VoiceCheckAdapterContract
from app.schemas.constants.assistants import AutotestCheckCode, AutotestOutcome
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.autotest_runs import AutotestScenario
from app.schemas.dto.voice import VoiceAgentSpec
from app.schemas.dto.voice_checks import (
    VoiceCheckBatch,
    VoiceCheckCallContext,
    VoiceCheckCase,
    VoiceCheckOutcome,
    VoiceCheckRun,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.strings import AutotestCheckNote
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.channels.strings import CallLocalTimeText, CallNextDaysText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.voice_agent_specs import (
    VoiceAgentSources,
    build_voice_agent_spec,
)
from app.utilities.assembly.voice_check_evaluation import voice_check_result
from app.utilities.assembly.voice_check_scenarios import (
    build_caller_brief,
    build_condition,
    build_tool_mocks,
)
from app.utilities.conversations.tool_selection import select_voice_agent_tools
from app.utilities.conversations.turn_context import (
    describe_local_now,
    describe_next_days,
)
from app.utilities.scheduling.zoned_time import (
    load_time_zone,
    microseconds_to_seconds,
    to_local_moment,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
NOT_CONFIGURED_NOTE: str = (
    "The voice platform is not configured on this server: the simulated call "
    "was not played."
)
NOT_SET_UP_NOTE: str = (
    "The voice platform could not set up the agent of the voice checks."
)


class RunVoiceChecksUseCase(
    UseCaseContract[VoiceCheckRun, list[AutotestScenarioResult]]
):
    """
    Play the voice scenarios of a run (R16-VOICE-TUNING): the voice
    platform simulates a caller in each scenario's language against an
    agent built from the version under test exactly as publishing would
    build it (`build_voice_agent_spec`), with every tool mocked, and judges
    the call; `voice_check_result` adds the platform-independent checks.
    The results carry the channel PHONE. A BOOKING check is launch-critical
    like a chat booking, so a version whose voice books wrongly cannot go
    live.

    When the platform is not configured, or cannot set up the checks'
    agent, every voice scenario is ERRORED (never silently passed).
    """

    def __init__(
        self,
        voice_agent_sources: VoiceAgentSources,
        voice_check_adapter: VoiceCheckAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._sources: VoiceAgentSources = voice_agent_sources
        self._voice_checks: VoiceCheckAdapterContract = voice_check_adapter
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: VoiceCheckRun) -> list[AutotestScenarioResult]:
        scenarios: list[AutotestScenario] = input_data.scenarios
        if not scenarios:
            return []

        base_url: PublicBaseUrl | None = self._sources.app_settings.app_base_url
        if base_url is None or self._voice_checks.list_missing_settings():
            return [
                errored_result(scenario, NOT_CONFIGURED_NOTE) for scenario in scenarios
            ]

        try:
            spec: VoiceAgentSpec = build_voice_agent_spec(
                self._sources, input_data.business, input_data.version, None, base_url
            )
            outcomes: list[VoiceCheckOutcome] = self._voice_checks.run_checks(
                VoiceCheckBatch(
                    agent=spec,
                    cases=[self._case(input_data, scenario) for scenario in scenarios],
                )
            )
        except ApplicationError as error:
            LOGGER.warning(
                "The voice checks of autotest run %s were not played: %s",
                input_data.run_id,
                error,
            )
            return [errored_result(scenario, NOT_SET_UP_NOTE) for scenario in scenarios]

        greetings: dict[LanguageTag, MessageText] = {
            greeting.language: greeting.text for greeting in spec.greetings
        }
        return [
            voice_check_result(scenario, outcome, greetings.get(scenario.language))
            for scenario, outcome in zip(scenarios, outcomes, strict=True)
        ]

    def _case(self, run: VoiceCheckRun, scenario: AutotestScenario) -> VoiceCheckCase:
        business: BusinessDocument = run.business
        local_now: datetime = to_local_moment(
            microseconds_to_seconds(int(self._wall_clock.now_unix())),
            load_time_zone(business.timezone),
        )
        return VoiceCheckCase(
            key=scenario.key,
            language=scenario.language,
            brief=build_caller_brief(
                str(business.name),
                scenario,
                run.customer_phone_number,
                run.version.facts,
            ),
            condition=build_condition(scenario),
            call_context=VoiceCheckCallContext(
                local_now_text=CallLocalTimeText(describe_local_now(local_now)),
                next_days_text=CallNextDaysText(describe_next_days(local_now)),
                timezone=business.timezone,
            ),
            tool_mocks=build_tool_mocks(select_voice_agent_tools(run.version)),
        )


def errored_result(scenario: AutotestScenario, note: str) -> AutotestScenarioResult:
    return AutotestScenarioResult(
        scenario_key=scenario.key,
        kind=scenario.kind,
        language=scenario.language,
        outcome=AutotestOutcome.ERRORED,
        check_notes=[AutotestCheckNote(note)],
        check_codes=[AutotestCheckCode.CONVERSATION_FAILED],
        channel=ChannelKind.PHONE,
    )
