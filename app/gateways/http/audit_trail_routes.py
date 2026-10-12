"""The audit log's hash chains: the owner's check and the admin audit view."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.compliance import AuditAction, AuditSecurityEvent
from app.schemas.dto.audit_chain_views import (
    AdminAuditChainsQuery,
    AuditChainOverview,
    AuditChainStatusQuery,
    AuditChainStatusView,
    PlatformAuditLogPage,
    PlatformAuditLogQuery,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

type GetAuditChainStatusOperator = OperatorContract[
    AuditChainStatusQuery, AuditChainStatusView
]
type GetAuditChainOverviewOperator = OperatorContract[
    AdminAuditChainsQuery, AuditChainOverview
]
type ListPlatformAuditLogOperator = OperatorContract[
    PlatformAuditLogQuery, PlatformAuditLogPage
]


def build_audit_trail_router(
    get_audit_chain_status_operator: GetAuditChainStatusOperator,
    get_audit_chain_overview_operator: GetAuditChainOverviewOperator,
    list_platform_audit_log_operator: ListPlatformAuditLogOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (bearer token):
        GET /v1/businesses/{business_id}/audit-log/chain  owner: how the
            latest daily check of the business's audit chain went
        GET /v1/admin/audit-log          platform admin: the entries that
            name no business, newest first (?limit, ?cursor, ?action,
            ?security_event)
        GET /v1/admin/audit-log/chains   platform admin: the platform's
            chain, how many chains are intact and broken, the broken ones
    """

    router = APIRouter(tags=["audit"], responses=standard_error_responses())

    @router.get("/v1/businesses/{business_id}/audit-log/chain")
    def get_audit_chain_status(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AuditChainStatusView:
        return get_audit_chain_status_operator.operate(
            AuditChainStatusQuery(
                user_id=user_id,
                business_id=parse_path_identifier(business_id, BusinessId, "Business"),
            )
        )

    @router.get("/v1/admin/audit-log")
    def list_platform_audit_log(
        user_id: Annotated[UserId, Depends(current_user)],
        limit: str | None = None,
        cursor: str | None = None,
        action: str | None = None,
        security_event: str | None = None,
    ) -> PlatformAuditLogPage:
        return list_platform_audit_log_operator.operate(
            PlatformAuditLogQuery(
                user_id=user_id,
                page=parse_page_request(limit, cursor),
                action=parse_optional(action, AuditAction, "action"),
                security_event=parse_optional(
                    security_event, AuditSecurityEvent, "security_event"
                ),
            )
        )

    @router.get("/v1/admin/audit-log/chains")
    def get_audit_chain_overview(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AuditChainOverview:
        return get_audit_chain_overview_operator.operate(
            AdminAuditChainsQuery(user_id=user_id)
        )

    return router
