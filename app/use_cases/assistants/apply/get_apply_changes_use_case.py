from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.apply_changes import (
    ApplyChangesQuery,
    ApplyChangesSource,
    ApplyChangesView,
)


class GetApplyChangesUseCase(UseCaseContract[ApplyChangesQuery, ApplyChangesView]):
    """
    An owner or staff member follows "Apply changes" (the cabinet polls it
    while the checks run); texts in the owner's language by default.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        describe_apply_changes: UseCaseContract[ApplyChangesSource, ApplyChangesView],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._describe_apply_changes: UseCaseContract[
            ApplyChangesSource, ApplyChangesView
        ] = describe_apply_changes

    def run(self, input_data: ApplyChangesQuery) -> ApplyChangesView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        return self._describe_apply_changes.run(
            ApplyChangesSource(
                business=business,
                language=input_data.language or business.owner_language,
            )
        )
