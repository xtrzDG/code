"""Platform admin: every client, client health, entering a client's cabinet."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.strict_request_parsing import (
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin import (
    AdminClientList,
    AdminClientQuery,
    AdminClientsQuery,
    ClientCabinetAccess,
    ClientHealthView,
    OpenClientCabinetCommand,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

type ListClientsOperator = OperatorContract[AdminClientsQuery, AdminClientList]
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
        GET  /v1/admin/clients                          every client
        GET  /v1/admin/clients/{business_id}            one client in detail
        POST /v1/admin/clients/{business_id}/open       enter the cabinet
                                                        (audited)
    """

    router = APIRouter(tags=["admin"])

    @router.get("/v1/admin/clients")
    def list_clients(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AdminClientList:
        return list_clients_operator.operate(AdminClientsQuery(user_id=user_id))

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

    @router.post("/v1/admin/clients/{business_id}/open")
    def open_client_cabinet(
        request: Request,
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ClientCabinetAccess:
        return open_client_cabinet_operator.operate(
            OpenClientCabinetCommand(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
                client_ip_address=read_client_ip_address(request),
            )
        )

    return router
