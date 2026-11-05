"""
Platform admin: campaigns held over their opt-out rate (ABUSE-05), with
Bearer auth and a two-factor session.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin_campaign_holds import (
    CampaignHoldList,
    CampaignHoldView,
    ListCampaignHoldsQuery,
    ReleaseCampaignHoldBody,
    ReleaseCampaignHoldCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

CAMPAIGN_HOLDS_PATH: str = "/v1/admin/campaign-holds"


read_release_body = build_json_body_dependency(ReleaseCampaignHoldBody)


def build_admin_campaign_hold_router(
    *,
    current_user: CurrentUserDependency,
    list_campaign_holds: OperatorContract[ListCampaignHoldsQuery, CampaignHoldList],
    release_campaign_hold: OperatorContract[
        ReleaseCampaignHoldCommand, CampaignHoldView
    ],
) -> APIRouter:
    """
    Routes:
        GET /v1/admin/campaign-holds
            the held campaigns, the longest held first; admins who see
            operations
        POST /v1/admin/campaign-holds/{business_id}/release
            let a held campaign write again, with a reason; SUPER admins,
            audited in the business's log, its owners told; 404 without a
            campaign, 409 when it is not held
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get(CAMPAIGN_HOLDS_PATH)
    def list_admin_campaign_holds(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> CampaignHoldList:
        return list_campaign_holds.operate(ListCampaignHoldsQuery(user_id=user_id))

    @router.post(
        CAMPAIGN_HOLDS_PATH + "/{business_id}/release",
        openapi_extra=describe_json_body(ReleaseCampaignHoldBody),
    )
    def release_admin_campaign_hold(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ReleaseCampaignHoldBody, Depends(read_release_body)],
    ) -> CampaignHoldView:
        return release_campaign_hold.operate(
            ReleaseCampaignHoldCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                reason=body.reason,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
