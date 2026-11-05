from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.catalog.call_forwarding import (
    CallForwardingInstructions,
    CallForwardingInstructionsQuery,
    CallForwardingInstructionsRequest,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag


class CallForwardingInstructionsOrchestrator(
    OrchestratorContract[CallForwardingInstructionsRequest, CallForwardingInstructions]
):
    """
    Cabinet flow: check that the user may act on the business (owners and
    staff; a platform admin's access is audited), then build the forwarding
    instructions in the requested language or the owner's language.
    """

    def __init__(
        self,
        authorize_business_access_use_case: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        build_call_forwarding_instructions_use_case: UseCaseContract[
            CallForwardingInstructionsQuery, CallForwardingInstructions
        ],
    ) -> None:
        self._authorize_business_access_use_case: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access_use_case
        self._build_call_forwarding_instructions_use_case: UseCaseContract[
            CallForwardingInstructionsQuery, CallForwardingInstructions
        ] = build_call_forwarding_instructions_use_case

    def execute(
        self,
        input_data: CallForwardingInstructionsRequest,
    ) -> CallForwardingInstructions:
        business: BusinessDocument = self._authorize_business_access_use_case.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        display_language: LanguageTag = (
            input_data.display_language
            if input_data.display_language is not None
            else business.owner_language
        )
        return self._build_call_forwarding_instructions_use_case.run(
            CallForwardingInstructionsQuery(
                business=business,
                display_language=display_language,
            )
        )
