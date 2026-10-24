from app.contracts.platform_status import PlatformAnnouncementRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.platform_status import PlatformAnnouncementDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.dto.platform_announcements import (
    AnnouncementPage,
    AnnouncementsQuery,
)
from app.use_cases.platform_status.announcement_views import admin_view
from app.utilities.paging.keyset_paging import finish_page, read_slice


class ListAnnouncementsUseCase(UseCaseContract[AnnouncementsQuery, AnnouncementPage]):
    """
    GET /v1/admin/announcements: every announcement with all its texts,
    newest first, paged by the database (keyset on the creation time).
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        announcement_repo: PlatformAnnouncementRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._announcement_repo: PlatformAnnouncementRepoContract = announcement_repo

    def run(self, input_data: AnnouncementsQuery) -> AnnouncementPage:
        self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(
                user_id=input_data.user_id,
                permission=PlatformAdminPermission.VIEW_OPERATIONS,
            )
        )
        fetched: list[PlatformAnnouncementDocument] = self._announcement_repo.list_page(
            read_slice(input_data.page)
        )
        announcements, next_cursor = finish_page(
            fetched,
            input_data.page,
            sort_key=lambda announcement: int(announcement.created_at),
            item_id=lambda announcement: str(announcement.id),
        )
        return AnnouncementPage(
            items=[admin_view(announcement) for announcement in announcements],
            next_cursor=next_cursor,
        )
