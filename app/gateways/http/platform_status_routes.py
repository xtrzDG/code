"""
The public status page's data and the platform admin's announcements
(the banner over every cabinet and the status page's notices).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    AnnouncementPage,
    AnnouncementsQuery,
    CreateAnnouncementBody,
    CreateAnnouncementCommand,
    UpdateAnnouncementBody,
    UpdateAnnouncementCommand,
)
from app.schemas.dto.platform_status import PlatformStatusQuery, PlatformStatusView
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.users.prefixed_id import UserId

type PlatformStatusOperator = OperatorContract[PlatformStatusQuery, PlatformStatusView]
type CreateAnnouncementOperator = OperatorContract[
    CreateAnnouncementCommand, AnnouncementAdminView
]
type UpdateAnnouncementOperator = OperatorContract[
    UpdateAnnouncementCommand, AnnouncementAdminView
]
type ListAnnouncementsOperator = OperatorContract[AnnouncementsQuery, AnnouncementPage]

read_create_body = build_json_body_dependency(CreateAnnouncementBody)
read_update_body = build_json_body_dependency(UpdateAnnouncementBody)
# Many pages poll the status (the banner, the status page): a short shared
# cache keeps them cheap and still current within a minute.
STATUS_CACHE_CONTROL: str = "public, max-age=30"


def build_platform_status_router(
    get_platform_status_operator: PlatformStatusOperator,
    create_announcement_operator: CreateAnnouncementOperator,
    update_announcement_operator: UpdateAnnouncementOperator,
    list_announcements_operator: ListAnnouncementsOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes:
        GET   /v1/platform/status?language=     public: each component now and
              over 90 days, the announcements shown now and the past ones
        POST  /v1/admin/announcements           platform admin: announce
              (201; step-up; audited)
        PATCH /v1/admin/announcements/{id}      platform admin: change or
              resolve (`resolve: true`; step-up; audited)
        GET   /v1/admin/announcements           platform admin: every
              announcement, newest first ?limit=&cursor=
    """

    router = APIRouter(tags=["platform status"], responses=standard_error_responses())

    @router.get("/v1/platform/status")
    def get_platform_status(
        response: Response, language: str | None = None
    ) -> PlatformStatusView:
        response.headers["Cache-Control"] = STATUS_CACHE_CONTROL
        return get_platform_status_operator.operate(
            PlatformStatusQuery(language=parse_language_parameter(language))
        )

    @router.post(
        "/v1/admin/announcements",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CreateAnnouncementBody),
    )
    def create_announcement(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CreateAnnouncementBody, Depends(read_create_body)],
    ) -> AnnouncementAdminView:
        return create_announcement_operator.operate(
            CreateAnnouncementCommand(
                user_id=user_id,
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.patch(
        "/v1/admin/announcements/{announcement_id}",
        openapi_extra=describe_json_body(UpdateAnnouncementBody),
    )
    def update_announcement(
        announcement_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[UpdateAnnouncementBody, Depends(read_update_body)],
    ) -> AnnouncementAdminView:
        return update_announcement_operator.operate(
            UpdateAnnouncementCommand(
                user_id=user_id,
                announcement_id=parse_path_identifier(
                    announcement_id, AnnouncementId, "Announcement"
                ),
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/admin/announcements")
    def list_announcements(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> AnnouncementPage:
        return list_announcements_operator.operate(
            AnnouncementsQuery(user_id=user_id, page=parse_page_request(limit, cursor))
        )

    return router
