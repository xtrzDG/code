import logging

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.inbox import InboxView
from app.schemas.dto.handoffs import HandoffCommand, HandoffResult
from app.schemas.dto.inbox.assignment import AutoAssignCommand, AutoAssignResult
from app.schemas.exceptions.base_exception import ApplicationError

LOGGER: logging.Logger = logging.getLogger(__name__)


class AutoAssigningHandoffUseCase(UseCaseContract[HandoffCommand, HandoffResult]):
    """
    Pass a conversation to staff (`HandoffToHumanUseCase`, which this wraps
    for every caller: the model tool, the reply guard, phone calls), then
    let the team inbox assign the new handoff automatically when the
    business asked for that. The handoff never depends on the assignment:
    it is stored and staff are notified first, and a failed assignment is
    logged, not raised (the handoff waits unassigned in the inbox).
    """

    def __init__(
        self,
        handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult],
        auto_assign: UseCaseContract[AutoAssignCommand, AutoAssignResult],
    ) -> None:
        self._handoff_to_human: UseCaseContract[HandoffCommand, HandoffResult] = (
            handoff_to_human
        )
        self._auto_assign: UseCaseContract[AutoAssignCommand, AutoAssignResult] = (
            auto_assign
        )

    def run(self, input_data: HandoffCommand) -> HandoffResult:
        result: HandoffResult = self._handoff_to_human.run(input_data)
        try:
            self._auto_assign.run(
                AutoAssignCommand(
                    business_id=result.business_id,
                    conversation_id=result.conversation_id,
                    trigger=InboxView.NEEDS_PERSON,
                    is_sandbox=input_data.is_sandbox,
                )
            )
        except ApplicationError:
            LOGGER.exception(
                "Handoff %s could not be assigned automatically.", result.id
            )

        return result
