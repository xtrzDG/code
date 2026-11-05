"""The voice checks of a started autotest run, apart from its test chats."""

from collections.abc import Sequence

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.assistants.autotest_runs import AutotestRunPlan, AutotestScenario
from app.schemas.dto.voice_checks import VoiceCheckRun


def split_voice_checks(
    scenarios: Sequence[AutotestScenario],
) -> tuple[list[AutotestScenario], list[AutotestScenario]]:
    """(the test chats, the voice checks), each in plan order."""

    return (
        [
            scenario
            for scenario in scenarios
            if scenario.channel is not ChannelKind.PHONE
        ],
        [scenario for scenario in scenarios if scenario.channel is ChannelKind.PHONE],
    )


def voice_check_run(
    plan: AutotestRunPlan, scenarios: list[AutotestScenario]
) -> VoiceCheckRun:
    return VoiceCheckRun(
        run_id=plan.run_id,
        business=plan.business,
        version=plan.version,
        scenarios=scenarios,
        customer_phone_number=plan.customer_phone_number,
    )
