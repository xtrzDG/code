from app.contracts.repositories import AssistantVersionRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.dto.conversation_feed import OwnerTestChatVersionQuery
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId

# Before the first publication the owner tests the newest ready version, or
# else the newest draft.
FALLBACK_STATUSES: tuple[AssistantVersionStatus, ...] = (
    AssistantVersionStatus.READY,
    AssistantVersionStatus.DRAFT,
)


class ResolveTestChatVersionUseCase(
    UseCaseContract[OwnerTestChatVersionQuery, AssistantVersionId]
):
    """
    The assistant version that answers the owner's test chat: the requested
    version (of this business), else the published one, else the newest
    ready version, else the newest draft.
    """

    def __init__(self, assistant_version_repo: AssistantVersionRepoContract) -> None:
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )

    def run(self, input_data: OwnerTestChatVersionQuery) -> AssistantVersionId:
        if input_data.requested_version_id is not None:
            requested: AssistantVersionDocument | None = (
                self._assistant_version_repo.get(
                    input_data.business_id, input_data.requested_version_id
                )
            )
            if requested is None:
                raise NotFoundError(
                    f"Assistant version {input_data.requested_version_id} was not "
                    "found."
                )

            return requested.id

        if input_data.published_version_id is not None:
            return input_data.published_version_id

        versions: list[AssistantVersionDocument] = (
            self._assistant_version_repo.list_by_business(input_data.business_id)
        )
        for status in FALLBACK_STATUSES:
            candidates: list[AssistantVersionDocument] = [
                version for version in versions if version.status is status
            ]
            if candidates:
                return max(
                    candidates, key=lambda version: int(version.version_number)
                ).id

        raise ConflictError("The assistant has no version to test yet.")
