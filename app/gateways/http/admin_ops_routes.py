"""
Platform admin: the whole platform on one page and the incident log
(docs/operations/slo.md, docs/operations/incident.md).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.admin_system import AdminSystemQuery, AdminSystemView
from app.schemas.dto.incidents import (
    CreateIncidentBody,
    CreateIncidentCommand,
    IncidentPage,
    IncidentsQuery,
    IncidentView,
)
from app.schemas.typings.users.prefixed_id import UserId

type GetAdminSystemOperator = OperatorContract[AdminSystemQuery, AdminSystemView]
type CreateIncidentOperator = OperatorContract[CreateIncidentCommand, IncidentView]
type ListIncidentsOperator = OperatorContract[IncidentsQuery, IncidentPage]

read_incident_body = build_json_body_dependency(CreateIncidentBody)


def build_admin_ops_router(
    get_admin_system_operator: GetAdminSystemOperator,
    create_incident_operator: CreateIncidentOperator,
    list_incidents_operator: ListIncidentsOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token of a platform admin; others get 403):
        GET  /v1/admin/system      worker pulses, queue lanes, dead letters
             by job, channels in ERROR, Meta tokens that run out, database
             size per collection, the last backup and restore drill, and
             the platform alerts (indexed counts only)
        POST /v1/admin/incidents   record an incident (201; step-up; one
             audit entry per affected business); a data breach also tells
             every owner of those businesses through the outbox with the
             DPA 12.1 texts
        GET  /v1/admin/incidents   the incident log, newest first
             ?limit=&cursor=
    """

    router = APIRouter(tags=["admin"], responses=standard_error_responses())

    @router.get("/v1/admin/system")
    def get_admin_system(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AdminSystemView:
        return get_admin_system_operator.operate(AdminSystemQuery(user_id=user_id))

    @router.post(
        "/v1/admin/incidents",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CreateIncidentBody),
    )
    def create_incident(
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CreateIncidentBody, Depends(read_incident_body)],
    ) -> IncidentView:
        return create_incident_operator.operate(
            CreateIncidentCommand(
                user_id=user_id,
                body=body,
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get("/v1/admin/incidents")
    def list_incidents(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
    ) -> IncidentPage:
        return list_incidents_operator.operate(
            IncidentsQuery(user_id=user_id, page=parse_page_request(limit, cursor))
        )

    return router
