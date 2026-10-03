"""Routers of key management (platform admin)."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_security_routes import build_admin_security_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_security_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The key ring's view and its re-encryption run."""

    security = operators.security
    return [
        build_admin_security_router(
            get_encryption_keys_operator=security.get_encryption_keys_operator(),
            start_key_rotation_operator=security.start_key_rotation_operator(),
            current_user=current_user,
        )
    ]
