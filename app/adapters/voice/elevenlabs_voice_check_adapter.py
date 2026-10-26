"""The voice checks of autotests at ElevenLabs agent testing."""

import logging
import time
from collections.abc import Callable

from typed_time_provider import MonotonicClock, Nanoseconds

from app.adapters.voice.elevenlabs_tool_config import build_tool_config
from app.adapters.voice.elevenlabs_voice_check_bodies import (
    agent_config_override,
    build_check_agent_config,
    build_test_config,
    read_run_status,
    read_test_run,
)
from app.contracts.channel_clients import JsonObject
from app.contracts.voice_check_clients import ElevenLabsPlatformClientContract
from app.contracts.voice_platform import VoiceCheckAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.voice_checks import VoiceCheckStatus
from app.schemas.dto.voice_checks import (
    VoiceCheckBatch,
    VoiceCheckCase,
    VoiceCheckOutcome,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_strings import AutotestScenarioKey
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.strings import VoicePlatformToolId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.voice.constrained_integers import VoiceCheckWaitSeconds
from app.schemas.typings.voice.constrained_strings import (
    VoiceCheckInvocationId,
    VoiceCheckTestId,
)
from app.utilities.channels.channel_endpoints import VOICE_BUSINESS_ID_HEADER
from app.utilities.channels.json_values import read_objects, read_text

logger: logging.Logger = logging.getLogger(__name__)
NANOSECONDS_PER_SECOND: int = 1_000_000_000
DEFAULT_WAIT: VoiceCheckWaitSeconds = VoiceCheckWaitSeconds(600)
DEFAULT_POLL_SECONDS: float = 5.0

type StartedRun = tuple[VoiceCheckInvocationId, dict[VoiceCheckTestId, VoiceCheckCase]]


class ElevenLabsVoiceCheckAdapter(VoiceCheckAdapterContract):
    """
    Simulated calls at ElevenLabs agent testing (the successor of
    simulate-conversation, which ElevenLabs removes on 2026-10-31).

    One agent is built for the run from the version under test, tagged
    "voice-check" and attached to no number; its webhook tools carry the
    business id but no tool secret, so the platform's tool endpoints refuse
    a real call, and every test mocks every tool besides ("all", a tool
    without a mock fails instead of running). Each language's tests run in
    one invocation with the agent answering in that language first (its
    greeting and voice, `agent_config_override`); the invocations are
    polled every `poll_seconds` until they finish or `wait_seconds` pass.
    The tests, the agent and its tools are deleted afterwards, whatever
    happened.
    """

    def __init__(
        self,
        elevenlabs_client: ElevenLabsPlatformClientContract,
        app_settings: AppSettings,
        monotonic_clock: MonotonicClock[Nanoseconds],
        sleep: Callable[[float], None] = time.sleep,
        wait_seconds: VoiceCheckWaitSeconds = DEFAULT_WAIT,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        self._client: ElevenLabsPlatformClientContract = elevenlabs_client
        self._app_settings: AppSettings = app_settings
        self._monotonic_clock: MonotonicClock[Nanoseconds] = monotonic_clock
        self._sleep: Callable[[float], None] = sleep
        self._wait_nanoseconds: int = int(wait_seconds) * NANOSECONDS_PER_SECOND
        self._poll_seconds: float = poll_seconds

    def list_missing_settings(self) -> list[EnvironmentVariableName]:
        if self._app_settings.elevenlabs_api_key is None:
            return [EnvironmentVariableName("ELEVENLABS_API_KEY")]

        return []

    def run_checks(self, batch: VoiceCheckBatch) -> list[VoiceCheckOutcome]:
        if not batch.cases:
            return []

        headers: JsonObject = {VOICE_BUSINESS_ID_HEADER: str(batch.agent.business_id)}
        tool_ids: list[VoicePlatformToolId] = []
        test_ids: list[VoiceCheckTestId] = []
        agent_id: VoiceAgentId | None = None
        try:
            for tool in batch.agent.tools:
                tool_ids.append(
                    self._client.create_tool(
                        build_tool_config(
                            tool, str(batch.agent.tool_webhook_base_url), headers
                        )
                    )
                )

            agent_id = self._client.create_agent(
                build_check_agent_config(
                    batch.agent, tool_ids, headers, batch.agent.default_language
                )
            )
            outcomes: dict[AutotestScenarioKey, VoiceCheckOutcome] = {}
            runs: list[StartedRun] = []
            for language_cases in group_by_language(batch.cases):
                run: StartedRun | None = self._start(
                    batch,
                    agent_id,
                    tool_ids,
                    headers,
                    language_cases,
                    test_ids,
                    outcomes,
                )
                if run is not None:
                    runs.append(run)

            self._collect(runs, outcomes)
            return [outcomes.get(case.key, unfinished(case)) for case in batch.cases]
        finally:
            self._clean_up(agent_id, tool_ids, test_ids)

    def _start(
        self,
        batch: VoiceCheckBatch,
        agent_id: VoiceAgentId,
        tool_ids: list[VoicePlatformToolId],
        headers: JsonObject,
        cases: list[VoiceCheckCase],
        test_ids: list[VoiceCheckTestId],
        outcomes: dict[AutotestScenarioKey, VoiceCheckOutcome],
    ) -> StartedRun | None:
        """Create the language's tests and start them; None when refused."""

        tests: dict[VoiceCheckTestId, VoiceCheckCase] = {}
        try:
            for case in cases:
                test_id: VoiceCheckTestId = self._client.create_test(
                    build_test_config(case)
                )
                test_ids.append(test_id)
                tests[test_id] = case

            override: JsonObject = agent_config_override(
                build_check_agent_config(
                    batch.agent, tool_ids, headers, cases[0].language
                )
            )
            return (
                self._client.run_tests(agent_id, list(tests), override),
                tests,
            )
        except ExternalServiceError as error:
            logger.warning(
                "Voice checks in %s were not started: %s", cases[0].language, error
            )
            for case in cases:
                outcomes[case.key] = errored(case)
            return None

    def _collect(
        self,
        runs: list[StartedRun],
        outcomes: dict[AutotestScenarioKey, VoiceCheckOutcome],
    ) -> None:
        """Poll the runs until every test finished or the time is up."""

        deadline: int = self._now() + self._wait_nanoseconds
        pending: list[StartedRun] = list(runs)
        while pending and self._now() < deadline:
            self._sleep(self._poll_seconds)
            pending = [run for run in pending if not self._read(run, outcomes)]

    def _read(
        self,
        run: StartedRun,
        outcomes: dict[AutotestScenarioKey, VoiceCheckOutcome],
    ) -> bool:
        """
        Store the outcome of every test of the run that finished; True when
        none is left running.
        """

        invocation_id, tests = run
        try:
            invocation: JsonObject | None = self._client.get_test_invocation(
                invocation_id
            )
        except ExternalServiceError as error:
            logger.warning("Voice check run %s not read: %s", invocation_id, error)
            return False

        if invocation is None:
            for case in tests.values():
                outcomes[case.key] = errored(case)
            return True

        finished: dict[str, JsonObject] = {
            test_id: test_run
            for test_run in read_objects(invocation, "test_runs")
            for test_id in [read_text(test_run, "test_id") or ""]
            if read_run_status(test_run) is not None
        }
        for test_id, case in tests.items():
            if str(test_id) in finished:
                outcomes[case.key] = read_test_run(case, finished[str(test_id)])

        return all(str(test_id) in finished for test_id in tests)

    def _clean_up(
        self,
        agent_id: VoiceAgentId | None,
        tool_ids: list[VoicePlatformToolId],
        test_ids: list[VoiceCheckTestId],
    ) -> None:
        """The tests, then the agent, then its tools; each try on its own."""

        for test_id in test_ids:
            try_to_delete(self._client.delete_test, test_id)

        if agent_id is not None:
            try_to_delete(self._client.delete_agent, agent_id)

        for tool_id in tool_ids:
            try_to_delete(self._client.delete_tool, tool_id)

    def _now(self) -> int:
        return int(self._monotonic_clock.now_monotonic())


def try_to_delete[Target](remove: Callable[[Target], None], target: Target) -> None:
    try:
        remove(target)
    except ApplicationError as error:
        logger.warning("A voice check's leftover was not deleted: %s", error)


def group_by_language(cases: list[VoiceCheckCase]) -> list[list[VoiceCheckCase]]:
    """The cases of each language, languages in their first case's order."""

    groups: dict[str, list[VoiceCheckCase]] = {}
    for case in cases:
        groups.setdefault(str(case.language), []).append(case)

    return list(groups.values())


def errored(case: VoiceCheckCase) -> VoiceCheckOutcome:
    return VoiceCheckOutcome(key=case.key, status=VoiceCheckStatus.ERRORED)


def unfinished(case: VoiceCheckCase) -> VoiceCheckOutcome:
    return VoiceCheckOutcome(key=case.key, status=VoiceCheckStatus.UNFINISHED)
