from app.contracts.incidents import IncidentRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.incidents import IncidentPage, IncidentsQuery
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.use_cases.admin.incidents.incident_views import incident_view
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListIncidentsUseCase(UseCaseContract[IncidentsQuery, IncidentPage]):
    """
    GET /v1/admin/incidents: the incident log for a platform admin, newest
    first, paged by the database (keyset on the creation time).
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        incident_repo: IncidentRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._incident_repo: IncidentRepoContract = incident_repo

    def run(self, input_data: IncidentsQuery) -> IncidentPage:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        fetched: list[IncidentDocument] = self._incident_repo.list_page(
            read_slice(input_data.page)
        )
        incidents, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda incident: int(incident.created_at),
            item_id=lambda incident: str(incident.id),
        )
        return IncidentPage(
            items=[incident_view(incident) for incident in incidents],
            next_cursor=next_cursor,
        )
