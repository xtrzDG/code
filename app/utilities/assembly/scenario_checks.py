"""
Every deterministic check of one played autotest scenario: what was
created and in which language (`check_conversation`), the prices
(`autotest_price_checks`) and the attacks (`red_team_checks`).
"""

from collections.abc import Sequence

from app.schemas.dto.assistants.autotest_runs import (
    AutotestCheckFailure,
    AutotestScenarioRun,
)
from app.schemas.dto.conversations import AssistantReply
from app.utilities.assembly.autotest_evaluation import check_conversation
from app.utilities.assembly.autotest_price_checks import check_prices
from app.utilities.assembly.red_team_checks import check_attack


def check_scenario_run(
    scenario_run: AutotestScenarioRun, replies: Sequence[AssistantReply]
) -> list[AutotestCheckFailure]:
    """The failed checks of a scenario's conversation, in a fixed order."""

    return [
        *check_conversation(
            scenario_run.scenario, replies, str(scenario_run.business.name)
        ),
        *check_prices(
            scenario_run.scenario,
            replies,
            scenario_run.version.facts,
            scenario_run.business.currency_code,
        ),
        *check_attack(scenario_run, replies),
    ]
