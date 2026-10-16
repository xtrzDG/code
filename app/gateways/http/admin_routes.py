"""Platform admin: every client, client health, entering a client's cabinet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

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
from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.client_health import AdminClientSort, ClientHealthStatus
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.admin import (
    AdminClientPage,
    AdminClientQuery,
    AdminClientsQuery,
    ClientCabinetAccess,
    ClientHealthView,
    OpenClientCabinetCommand,
)
from app.schemas.dto.support_access import OpenClientCabinetRequest
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.constrained_strings import ClientSearchText
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.prefixed_id import UserId

read_open_body = build_json_body_dependency(OpenClientCabinetRequest)

type ListClientsOperator = OperatorContract[AdminClientsQuery, AdminClientPage]
type GetClientHealthOperator = OperatorContract[AdminClientQuery, ClientHealthView]
type OpenClientCabinetOperator = OperatorContract[
    OpenClientCabinetCommand,
    ClientCabinetAccess,
]


def build_admin_router(
    list_clients_operator: ListClientsOperator,
    get_client_health_operator: GetClientHealthOperator,
    open_client_cabinet_operator: OpenClientCabinetOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; others get 403):
        GET  /v1/admin/clients                          clients, one page
             ?limit=&cursor=&status=&health=&country=&niche=&search=&sort=
        GET  /v1/admin/clients/{business_id}            one client in detail
        POST /v1/admin/clients/{business_id}/open       look into the cabinet
             {"reason"}: an hour, read-only unless the owner allows
             changes; the owner is told (step-up; audited)
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/clients")
    def list_clients(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
        status: str | None = None,
        health: str | None = None,
        country: str | None = None,
        niche: str | None = None,
        search: str | None = None,
        sort: str | None = None,
    ) -> AdminClientPage:
        return list_clients_operator.operate(
            AdminClientsQuery(
                user_id=user_id,
                page=parse_page_request(limit, cursor),
                status=parse_optional(status, BusinessStatus, "status"),
                health=parse_optional(health, ClientHealthStatus, "health"),
                country_code=parse_optional(
                    None if country is None else country.strip().upper(),
                    CountryCode,
                    "country",
                ),
                niche_key=parse_optional(niche, NicheKey, "niche"),
                search=parse_optional(
                    None if search is None else search.strip(),
                    ClientSearchText,
                    "search",
                ),
                sort=parse_optional(sort, AdminClientSort, "sort")
                or AdminClientSort.HEALTH,
            )
        )

    @router.get("/v1/admin/clients/{business_id}")
    def get_client_health(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ClientHealthView:
        return get_client_health_operator.operate(
            AdminClientQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.post(
        "/v1/admin/clients/{business_id}/open",
        openapi_extra=describe_json_body(OpenClientCabinetRequest),
    )
    def open_client_cabinet(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[OpenClientCabinetRequest, Depends(read_open_body)],
    ) -> ClientCabinetAccess:
        return open_client_cabinet_operator.operate(
            OpenClientCabinetCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                reason=body.reason,
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
