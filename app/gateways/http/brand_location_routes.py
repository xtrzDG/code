"""
What a location sees of its brand (cabinet, bearer token): the facts the
brand shares, with the location's own replacements, and the plans priced
as the location is billed for them.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.billing_routes import parse_optional_language
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.brands.brand_knowledge import (
    LocationOverridesQuery,
    LocationSharedKnowledge,
)
from app.schemas.dto.brands.location_plans import (
    LocationPlanQuery,
    LocationPlanQuoteList,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

LOCATION_PATH: str = "/v1/businesses/{business_id}"


def build_brand_location_router(
    *,
    current_user: CurrentUserDependency,
    list_shared_knowledge: OperatorContract[
        LocationOverridesQuery, LocationSharedKnowledge
    ],
    quote_plans: OperatorContract[LocationPlanQuery, LocationPlanQuoteList],
) -> APIRouter:
    """
    Routes:
        GET /v1/businesses/{id}/brand/knowledge
                                the brand's shared facts, each with the
                                location's own item replacing it (members)
        GET /v1/businesses/{id}/billing/plans?language=
                                every plan priced as this business is billed
                                (owners): a further location of a brand at
                                the additional-location price, no setup fee
                                where another location carries the brand's
    """

    router = APIRouter(tags=["brands"], responses=standard_error_responses())

    def business_of(raw_business_id: str) -> BusinessId:
        return parse_path_identifier(raw_business_id, BusinessId, "Business")

    @router.get(f"{LOCATION_PATH}/brand/knowledge")
    def list_location_shared_knowledge(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> LocationSharedKnowledge:
        return list_shared_knowledge.operate(
            LocationOverridesQuery(
                user_id=user_id, business_id=business_of(business_id)
            )
        )

    @router.get(f"{LOCATION_PATH}/billing/plans")
    def quote_location_plans(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: str | None = None,
    ) -> LocationPlanQuoteList:
        return quote_plans.operate(
            LocationPlanQuery(
                user_id=user_id,
                business_id=business_of(business_id),
                display_language=parse_optional_language(language),
            )
        )

    return router
