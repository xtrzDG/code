from app.contracts.repositories import AssistantVersionRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import (
    AssistantVersionRefusalCode,
    AssistantVersionStatus,
)
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import (
    AssistantVersionActivation,
    AssistantVersionDetails,
    RollbackAssistantVersionCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.utilities.assembly.go_live_refusals import build_version_reason


class RollbackAssistantVersionUseCase(
    UseCaseContract[RollbackAssistantVersionCommand, AssistantVersionDetails]
):
    """
    Owner publishes an earlier version again with one button (concept
    section 4). Only an ARCHIVED version, one that was live before, can be
    rolled back to (else the refusal reason is "version_not_archived"); the
    current live version is archived in its place. The go-live checks of
    activation apply, except the autotests.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ],
        version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._activate_assistant_version: UseCaseContract[
            AssistantVersionActivation,
            AssistantVersionDocument,
        ] = activate_assistant_version
        self._version_details_transformer: TransformerContract[
            AssistantVersionDocument,
            AssistantVersionDetails,
        ] = version_details_transformer

    def run(
        self, input_data: RollbackAssistantVersionCommand
    ) -> AssistantVersionDetails:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            business.id,
            input_data.version_id,
        )
        if version is None:
            raise NotFoundError(
                f"Assistant version {input_data.version_id} was not found."
            )

        if version.status is not AssistantVersionStatus.ARCHIVED:
            message: str = (
                f"Only an earlier live version can be rolled back to; version "
                f"{version.version_number} is {version.status.value}."
            )
            raise ConflictError(
                message,
                reasons=[
                    build_version_reason(
                        AssistantVersionRefusalCode.VERSION_NOT_ARCHIVED,
                        message,
                        [version.status.value],
                    )
                ],
            )

        published_version: AssistantVersionDocument = (
            self._activate_assistant_version.run(
                AssistantVersionActivation(business=business, version=version)
            )
        )
        return self._version_details_transformer.transform(published_version)
