"""The cabinet's search (Cmd/Ctrl+K): customers, conversations and bookings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.search import BusinessSearchQuery, BusinessSearchResults
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.search.constrained_strings import CabinetSearchText
from app.schemas.typings.users.prefixed_id import UserId


def build_search_router(
    *,
    current_user: CurrentUserDependency,
    search: OperatorContract[BusinessSearchQuery, BusinessSearchResults],
) -> APIRouter:
    """
    Routes (Bearer auth; owners and staff):
        GET /v1/businesses/{business_id}/search?q=   grouped hits (a few each)
    """

    router = APIRouter(tags=["customers"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/search")
    def search_business(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        q: str = "",
    ) -> BusinessSearchResults:
        return search.operate(
            BusinessSearchQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                text=parse_search_text(q),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router


def parse_search_text(raw: str) -> CabinetSearchText:
    """The typed search: 1 to 100 characters once trimmed; 422 otherwise."""

    try:
        return CabinetSearchText(raw.strip())
    except (ValueError, TypeError) as error:
        raise ValidationFailedError("q must hold 1 to 100 characters.") from error
