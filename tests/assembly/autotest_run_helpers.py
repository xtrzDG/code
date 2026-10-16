"""Starting an autotest run on a seeded testbed and reading its results."""

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    AutotestRunView,
    AutotestScenarioResultView,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.autotest_scenarios import RED_TEAM_SCENARIO_KINDS
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed

# The attacks every version plays once, in English, whatever its languages.
RED_TEAM_SCENARIO_COUNT: int = len(RED_TEAM_SCENARIO_KINDS)
GEORGIAN_SCENARIO_COUNT: int = 3 * 9 + 2 + RED_TEAM_SCENARIO_COUNT


def start(
    testbed: AssemblyTestbed,
    seed: BusinessDocument | None = None,
) -> tuple[BusinessDocument, AssistantVersionDetails]:
    business = seed or seed_georgian_restaurant(testbed)
    return business, testbed.assemble(business.id)


def results_by_key(run: AutotestRunView) -> dict[str, AutotestScenarioResultView]:
    return {str(result.scenario_key): result for result in run.results}


def run_one(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    version: AssistantVersionDetails,
    language: str,
    kind: AutotestScenarioKind,
) -> AutotestRunView:
    testbed.advance(60)
    return testbed.run_autotests_orchestrator.execute(
        RunAutotestsCommand(
            user_id=testbed.owner_id,
            business_id=business.id,
            version_id=version.id,
            languages=[LanguageTag(language)],
            kinds=[kind],
        )
    )
