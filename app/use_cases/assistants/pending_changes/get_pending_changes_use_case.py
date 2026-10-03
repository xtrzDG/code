from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.setup.pending_changes import (
    PendingChange,
    PendingChangesQuery,
    PendingChangesRequest,
    PendingChangesView,
)
from app.schemas.typings.setup.constrained_integers import PendingChangeCount


class GetPendingChangesUseCase(
    UseCaseContract[PendingChangesQuery, PendingChangesView]
):
    """
    An owner or staff member reads what customers do not get yet: every
    change since the live version, typed so the cabinet says it in the
    owner's words (niche questions in `language`, the owner's language by
    default). Before the first go-live nothing is compared: the view only
    says whether there is a profile to launch.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        assistant_version_repo: AssistantVersionRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        collect_pending_changes: UseCaseContract[
            PendingChangesRequest, list[PendingChange]
        ],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._collect_pending_changes: UseCaseContract[
            PendingChangesRequest, list[PendingChange]
        ] = collect_pending_changes

    def run(self, input_data: PendingChangesQuery) -> PendingChangesView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        live: AssistantVersionDocument | None = (
            None
            if business.published_assistant_version_id is None
            else self._assistant_version_repo.get(
                business.id, business.published_assistant_version_id
            )
        )
        if live is None:
            return PendingChangesView(
                business_id=business.id,
                is_live=False,
                has_unapplied_changes=(
                    self._business_profile_repo.get_by_business(business.id) is not None
                ),
                count=PendingChangeCount(0),
            )

        changes: list[PendingChange] = self._collect_pending_changes.run(
            PendingChangesRequest(
                business=business,
                version=live,
                language=input_data.language or business.owner_language,
            )
        )
        return PendingChangesView(
            business_id=business.id,
            is_live=True,
            live_version_number=live.version_number,
            has_unapplied_changes=bool(changes),
            count=PendingChangeCount(len(changes)),
            changes=changes,
        )
