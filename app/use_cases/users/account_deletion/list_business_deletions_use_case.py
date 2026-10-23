from app.contracts.repositories.business_closure_repositories import (
    BusinessDeletionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.business_closures import BusinessDeletionState
from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.dto.business_closures.business_deletions import (
    BusinessDeletionList,
    BusinessDeletionView,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId

# A person owned this many deleted businesses at most, in any real account.
LISTED_DELETIONS: DocumentQueryLimit = DocumentQueryLimit(200)


class ListBusinessDeletionsUseCase(UseCaseContract[UserId, BusinessDeletionList]):
    """
    The businesses a person owned that were deleted (or are being deleted),
    newest first: Account lists them with their deletion certificates.
    """

    def __init__(self, deletion_repo: BusinessDeletionRepoContract) -> None:
        self._deletion_repo: BusinessDeletionRepoContract = deletion_repo

    def run(self, input_data: UserId) -> BusinessDeletionList:
        entries: list[BusinessDeletionDocument] = self._deletion_repo.list_of_owner(
            input_data, LISTED_DELETIONS
        )
        return BusinessDeletionList(items=[deletion_view(entry) for entry in entries])


def deletion_view(entry: BusinessDeletionDocument) -> BusinessDeletionView:
    return BusinessDeletionView(
        id=entry.id,
        business_name=entry.business_name,
        reason=entry.reason,
        state=(
            BusinessDeletionState.COMPLETED
            if entry.completed_at is not None
            else BusinessDeletionState.IN_PROGRESS
        ),
        started_at=entry.started_at,
        completed_at=entry.completed_at,
    )
