"""Bookings → Return visits: the rebooking campaign and the messages it wrote."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.growth.campaign_views import (
    CampaignMessagePage,
    CampaignMessagePageQuery,
    CampaignSettingsQuery,
    CampaignSettingsRequest,
    CampaignSettingsView,
    UpdateCampaignSettingsCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_settings_body = build_json_body_dependency(CampaignSettingsRequest)
B: str = "/v1/businesses/{business_id}"


def business(raw_id: str) -> BusinessId:
    return parse_path_identifier(raw_id, BusinessId, "Business")


def build_return_visit_router(
    current_user: CurrentUserDependency,
    get_settings: OperatorContract[CampaignSettingsQuery, CampaignSettingsView],
    update_settings: OperatorContract[
        UpdateCampaignSettingsCommand, CampaignSettingsView
    ],
    list_messages: OperatorContract[CampaignMessagePageQuery, CampaignMessagePage],
) -> APIRouter:
    """
    Routes (all require a bearer token):
        GET /v1/businesses/{business_id}/campaign-settings
                    the rebooking campaign (the niche's rule, off until the
                    owner opts in), this month against the cap, the last 30
                    days by status, the message in each language; members
        PUT /v1/businesses/{business_id}/campaign-settings
                    {is_enabled, rule_kind, delay_days, audience, segment_id,
                    monthly_cap} (owners; audited)
        GET /v1/businesses/{business_id}/campaign-messages?limit=&cursor=
                    whom the campaign wrote to or skipped, and who booked
                    again, the latest first (owners; audited)
    """

    router = APIRouter(tags=["return visits"], responses=standard_error_responses())

    @router.get(f"{B}/campaign-settings")
    def get_campaign_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CampaignSettingsView:
        return get_settings.operate(
            CampaignSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/campaign-settings",
        openapi_extra=describe_json_body(CampaignSettingsRequest),
    )
    def update_campaign_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CampaignSettingsRequest, Depends(read_settings_body)],
    ) -> CampaignSettingsView:
        return update_settings.operate(
            UpdateCampaignSettingsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.get(f"{B}/campaign-messages")
    def list_campaign_messages(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> CampaignMessagePage:
        return list_messages.operate(
            CampaignMessagePageQuery(
                user_id=user_id,
                business_id=business(business_id),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
