"""An owner's invitation and "Powered by" link, and a partner's portal."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.referrals.partner_portal import (
    CommissionEntryPage,
    PartnerPageQuery,
    PartnerPortalQuery,
    PartnerPortalView,
    PartnerReferralPage,
)
from app.schemas.dto.referrals.program import (
    PoweredByCommand,
    PoweredByRequest,
    PoweredByView,
    ReferralProgramQuery,
    ReferralProgramView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

REFERRALS_PATH: str = "/v1/businesses/{business_id}/referrals"
POWERED_BY_PATH: str = "/v1/businesses/{business_id}/referrals/powered-by"

read_powered_by_body = build_json_body_dependency(PoweredByRequest)


def build_referral_router(
    current_user: CurrentUserDependency,
    get_referral_program: OperatorContract[ReferralProgramQuery, ReferralProgramView],
    set_powered_by: OperatorContract[PoweredByCommand, PoweredByView],
    get_partner_portal: OperatorContract[PartnerPortalQuery, PartnerPortalView],
    list_partner_referrals: OperatorContract[PartnerPageQuery, PartnerReferralPage],
    list_partner_commissions: OperatorContract[PartnerPageQuery, CommissionEntryPage],
) -> APIRouter:
    """
    Routes (bearer token):
        GET /v1/businesses/{business_id}/referrals (owners)
            the business's invitation: code, link, invited, paid and
            rewarded businesses, whether the Overview card is due, and the
            "Powered by" link
        PUT /v1/businesses/{business_id}/referrals/powered-by (owners)
            leave the "Powered by" link off or bring it back (Plus; 409
            plan_required otherwise)
        GET /v1/partner
            the signed-in partner's portal (404 for anyone else)
        GET /v1/partner/referrals?limit=&cursor=
            the businesses the partner brought, newest first
        GET /v1/partner/commissions?limit=&cursor=
            the partner's commissions, newest first
    """

    router: APIRouter = APIRouter(
        tags=["referrals"], responses=standard_error_responses()
    )

    @router.get(REFERRALS_PATH)
    def get_referrals(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ReferralProgramView:
        return get_referral_program.operate(
            ReferralProgramQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.put(POWERED_BY_PATH, openapi_extra=describe_json_body(PoweredByRequest))
    def put_powered_by(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[PoweredByRequest, Depends(read_powered_by_body)],
    ) -> PoweredByView:
        return set_powered_by.operate(
            PoweredByCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                request=body,
            )
        )

    @router.get("/v1/partner")
    def get_partner(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> PartnerPortalView:
        return get_partner_portal.operate(PartnerPortalQuery(user_id=user_id))

    @router.get("/v1/partner/referrals")
    def get_partner_referrals(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> PartnerReferralPage:
        return list_partner_referrals.operate(
            PartnerPageQuery(user_id=user_id, page=parse_page_request(limit, cursor))
        )

    @router.get("/v1/partner/commissions")
    def get_partner_commissions(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> CommissionEntryPage:
        return list_partner_commissions.operate(
            PartnerPageQuery(user_id=user_id, page=parse_page_request(limit, cursor))
        )

    return router
