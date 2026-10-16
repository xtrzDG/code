from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
)
from app.contracts.repositories.autotest_case_repositories import (
    AutotestCaseRepoContract,
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
    PendingDraftView,
    PendingOwnerCheckView,
)
from app.schemas.typings.setup.constrained_integers import PendingChangeCount
from app.utilities.assembly.owner_check_coverage import (
    describe_owner_check_changes,
    is_owner_check_change,
)
from app.utilities.assembly.version_retirement import list_pending_drafts


class GetPendingChangesUseCase(
    UseCaseContract[PendingChangesQuery, PendingChangesView]
):
    """
    An owner or staff member reads what customers do not get yet: every
    change since the live version, typed so the cabinet says it in the
    owner's words (niche questions in `language`, the owner's language by
    default), the owner's checks the live version was not checked against
    (with what each asks, in a list of their own), and the drafts built
    since that customers never got. Before the first go-live nothing is
    compared: the view only says whether there is a profile to launch.
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
        autotest_case_repo: AutotestCaseRepoContract,
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
        self._autotest_case_repo: AutotestCaseRepoContract = autotest_case_repo

    def run(self, input_data: PendingChangesQuery) -> PendingChangesView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        versions: list[AssistantVersionDocument] = (
            self._assistant_version_repo.list_by_business(business.id)
        )
        live: AssistantVersionDocument | None = next(
            (
                version
                for version in versions
                if version.id == business.published_assistant_version_id
            ),
            None,
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
        owner_checks: list[PendingOwnerCheckView] = (
            describe_owner_check_changes(
                changes, self._autotest_case_repo.list_by_business(business.id)
            )
            if any(is_owner_check_change(change) for change in changes)
            else []
        )
        business_changes: list[PendingChange] = [
            change for change in changes if not is_owner_check_change(change)
        ]
        return PendingChangesView(
            business_id=business.id,
            is_live=True,
            live_version_number=live.version_number,
            has_unapplied_changes=bool(business_changes or owner_checks),
            count=PendingChangeCount(len(business_changes) + len(owner_checks)),
            changes=business_changes,
            owner_checks=owner_checks,
            drafts=[
                PendingDraftView(
                    assistant_version_id=draft.id,
                    version_number=draft.version_number,
                    status=draft.status,
                    created_at=draft.created_at,
                )
                for draft in list_pending_drafts(versions, live)
            ],
        )
