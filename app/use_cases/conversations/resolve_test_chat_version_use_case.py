from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.dto.conversation_feed.owner_test_chat import OwnerTestChatVersionQuery
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId

# Versions the owner may talk to: everything but archived ones.
TESTABLE_STATUSES: frozenset[AssistantVersionStatus] = frozenset(
    {
        AssistantVersionStatus.PUBLISHED,
        AssistantVersionStatus.READY,
        AssistantVersionStatus.TESTS_FAILED,
        AssistantVersionStatus.TESTING,
        AssistantVersionStatus.DRAFT,
    }
)


class ResolveTestChatVersionUseCase(
    UseCaseContract[OwnerTestChatVersionQuery, AssistantVersionId]
):
    """
    The assistant version that answers the owner's test chat: the requested
    version (of this business), else the newest version that is not
    archived - the one being prepared (ready, failed, under test or a
    draft) when it is newer than the live one, else the live one.
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

        candidates: list[AssistantVersionDocument] = [
            version
            for version in self._assistant_version_repo.list_by_business(
                input_data.business_id
            )
            if version.status in TESTABLE_STATUSES
        ]
        if candidates:
            return max(candidates, key=lambda version: int(version.version_number)).id

        if input_data.published_version_id is not None:
            return input_data.published_version_id

        raise ConflictError("The assistant has no version to test yet.")
