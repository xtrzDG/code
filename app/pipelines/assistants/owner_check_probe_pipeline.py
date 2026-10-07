from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.turn_slots import TurnSlotRegistryContract
from app.schemas.dto.assistants.autotest_cases import (
    OwnerCheckOutcomeView,
    OwnerCheckProbeCommand,
)


class OwnerCheckProbePipeline(
    PipelineContract[OwnerCheckProbeCommand, OwnerCheckOutcomeView]
):
    """
    "Check now" in the request: the owner waits for the test conversation,
    so it takes one of the test chat's places (TEST_CHAT_MAX_CONCURRENCY
    per API process) and never the threads the cabinet needs; beyond them
    the owner is asked to try again in a moment (429).
    """

    def __init__(
        self,
        check_owner_check_now: OrchestratorContract[
            OwnerCheckProbeCommand, OwnerCheckOutcomeView
        ],
        test_chat_slots: TurnSlotRegistryContract,
    ) -> None:
        self._check_owner_check_now: OrchestratorContract[
            OwnerCheckProbeCommand, OwnerCheckOutcomeView
        ] = check_owner_check_now
        self._test_chat_slots: TurnSlotRegistryContract = test_chat_slots

    def start(self, input_data: OwnerCheckProbeCommand) -> OwnerCheckOutcomeView:
        with self._test_chat_slots.hold():
            return self._check_owner_check_now.execute(input_data)
