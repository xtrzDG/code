from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import BusinessAccessMode
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.privacy.business_exports import (
    BusinessExportList,
    BusinessExportListQuery,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.exports.business_export_views import build_export_view

LISTED: DocumentQueryLimit = DocumentQueryLimit(10)


class ListBusinessExportsUseCase(
    UseCaseContract[BusinessExportListQuery, BusinessExportList]
):
    """
    The business's latest full exports, the newest first, each with how
    many downloads it has left. The archives are the business's data, so
    the list is the owner's alone (never staff or read-only support); a
    download needs a one-time link (CreateExportDownloadLinkUseCase).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        export_repo: BusinessExportRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._export_repo: BusinessExportRepoContract = export_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: BusinessExportListQuery) -> BusinessExportList:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
                access_mode=BusinessAccessMode.WRITE,
            )
        )
        now: Microseconds = self._wall_clock.now_unix()
        return BusinessExportList(
            items=[
                build_export_view(export, now)
                for export in self._export_repo.list_latest(business.id, LISTED)
            ]
        )
