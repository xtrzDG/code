from app.contracts.repositories import AssistantVersionRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.assistants import (
    AssistantVersionActivation,
    AssistantVersionDetails,
    PublishAssistantVersionCommand,
)
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.booleans import AcceptsFailedAutotests

UNTESTED_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {AssistantVersionStatus.DRAFT, AssistantVersionStatus.TESTS_FAILED}
)


class PublishAssistantVersionUseCase(
    UseCaseContract[PublishAssistantVersionCommand, AssistantVersionDetails]
):
    """
    Owner switches the assistant to a version ("Включить", concept section 4).

    A READY version is published; a DRAFT or TESTS_FAILED one only when the
    owner explicitly accepts the failed tests. A version under test, an
    already published one and an archived one (use rollback) are conflicts.
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
        self, input_data: PublishAssistantVersionCommand
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

        self._require_publishable(version, input_data.accept_failed_tests)
        published_version: AssistantVersionDocument = (
            self._activate_assistant_version.run(
                AssistantVersionActivation(business=business, version=version)
            )
        )
        return self._version_details_transformer.transform(published_version)

    def _require_publishable(
        self,
        version: AssistantVersionDocument,
        accept_failed_tests: AcceptsFailedAutotests,
    ) -> None:
        if version.status is AssistantVersionStatus.READY:
            return

        if version.status in UNTESTED_STATUSES:
            if accept_failed_tests:
                return

            raise ConflictError(
                f"Version {version.version_number} has not passed the autotests "
                f"(status {version.status.value}). Run the autotests, or publish "
                "with accept_failed_tests."
            )

        if version.status is AssistantVersionStatus.TESTING:
            raise ConflictError(
                f"Version {version.version_number} is being tested; publish it "
                "when the autotests finish."
            )

        if version.status is AssistantVersionStatus.PUBLISHED:
            raise ConflictError(f"Version {version.version_number} is already live.")

        raise ConflictError(
            f"Version {version.version_number} is archived; use rollback to "
            "publish it again."
        )
