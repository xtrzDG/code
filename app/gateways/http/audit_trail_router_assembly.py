"""Router of the audit log's hash chains (the owner's check, the admin view)."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.audit_trail_routes import build_audit_trail_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_audit_trail_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    audit_trail = operators.audit_trail
    return [
        build_audit_trail_router(
            get_audit_chain_status_operator=(
                audit_trail.get_audit_chain_status_operator()
            ),
            get_audit_chain_overview_operator=(
                audit_trail.get_audit_chain_overview_operator()
            ),
            list_platform_audit_log_operator=(
                audit_trail.list_platform_audit_log_operator()
            ),
            current_user=current_user,
        )
    ]
