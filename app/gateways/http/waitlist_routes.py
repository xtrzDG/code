"""Bookings → Waitlist: the customers waiting for a place, and its settings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.waitlist import WaitlistListFilter
from app.schemas.dto.growth.waitlist_views import (
    RemoveWaitlistEntryCommand,
    UpdateWaitlistSettingsCommand,
    WaitlistEntryPage,
    WaitlistPageQuery,
    WaitlistSettingsQuery,
    WaitlistSettingsRequest,
    WaitlistSettingsView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.waitlist.prefixed_id import WaitlistEntryId

read_settings_body = build_json_body_dependency(WaitlistSettingsRequest)
B: str = "/v1/businesses/{business_id}"


def business(raw_id: str) -> BusinessId:
    return parse_path_identifier(raw_id, BusinessId, "Business")


def build_waitlist_router(
    current_user: CurrentUserDependency,
    list_waitlist: OperatorContract[WaitlistPageQuery, WaitlistEntryPage],
    remove_entry: OperatorContract[RemoveWaitlistEntryCommand, None],
    get_settings: OperatorContract[WaitlistSettingsQuery, WaitlistSettingsView],
    update_settings: OperatorContract[
        UpdateWaitlistSettingsCommand, WaitlistSettingsView
    ],
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET    /v1/businesses/{business_id}/waitlist
                    ?filter=active|booked|ended&limit=&cursor=
                    the customers waiting (first come first) or done (the
                    latest first), with any place held for them; owners and
                    staff (customers' names: audited)
        DELETE /v1/businesses/{business_id}/waitlist/{entry_id}
                    a customer taken off the list (a held place goes to the
                    next); owners and staff, audited; 204
        GET    /v1/businesses/{business_id}/waitlist-settings
                    whether the business keeps a waitlist, the hold, counts
        PUT    /v1/businesses/{business_id}/waitlist-settings
                    {is_enabled, hold_minutes 15-120} (owners; audited)
    """

    router = APIRouter(tags=["waitlist"], responses=standard_error_responses())

    @router.get(f"{B}/waitlist")
    def list_waitlist_entries(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        list_filter: Annotated[str | None, Query(alias="filter")] = None,
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> WaitlistEntryPage:
        return list_waitlist.operate(
            WaitlistPageQuery(
                user_id=user_id,
                business_id=business(business_id),
                list_filter=parse_optional(list_filter, WaitlistListFilter, "filter")
                or WaitlistListFilter.ACTIVE,
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.delete(f"{B}/waitlist/{{entry_id}}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_waitlist_entry(
        business_id: str,
        entry_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        remove_entry.operate(
            RemoveWaitlistEntryCommand(
                user_id=user_id,
                business_id=business(business_id),
                entry_id=parse_path_identifier(
                    entry_id, WaitlistEntryId, "Waitlist entry"
                ),
                client_ip_address=read_client_ip_address(request),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(f"{B}/waitlist-settings")
    def get_waitlist_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> WaitlistSettingsView:
        return get_settings.operate(
            WaitlistSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/waitlist-settings",
        openapi_extra=describe_json_body(WaitlistSettingsRequest),
    )
    def update_waitlist_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[WaitlistSettingsRequest, Depends(read_settings_body)],
    ) -> WaitlistSettingsView:
        return update_settings.operate(
            UpdateWaitlistSettingsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    return router
