from collections.abc import Callable

from app.contracts.acting_user import ActingUserInputContract
from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.typings.users.booleans import IsPlatformAdmin
from app.schemas.typings.users.prefixed_id import UserId


class TeamViewOrchestrator[InputData: ActingUserInputContract, OutputData](
    OrchestratorContract[InputData, OutputData]
):
    """
    An endpoint whose answer holds platform details (OWASP API3, ASVS
    V15.3.1, API-05), such as the raw error text a provider answered: it
    runs the endpoint's orchestrator, then asks whether the person acting
    is a platform admin of now (read from the admin team at every call,
    never the stored flag). Anyone else, owners and staff included, gets
    the answer as the team sees it (`for_team`), so the API never sends
    what the interface would only hide.
    """

    def __init__(
        self,
        orchestrator: OrchestratorContract[InputData, OutputData],
        see_platform_details: UseCaseContract[UserId, IsPlatformAdmin],
        for_team: Callable[[OutputData], OutputData],
    ) -> None:
        self._orchestrator: OrchestratorContract[InputData, OutputData] = orchestrator
        self._see_platform_details: UseCaseContract[UserId, IsPlatformAdmin] = (
            see_platform_details
        )
        self._for_team: Callable[[OutputData], OutputData] = for_team

    def execute(self, input_data: InputData) -> OutputData:
        answer: OutputData = self._orchestrator.execute(input_data)
        if self._see_platform_details.run(input_data.user_id):
            return answer

        return self._for_team(answer)
