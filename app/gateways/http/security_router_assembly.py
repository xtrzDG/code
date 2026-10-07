"""Routers of key management (platform admin) and two-factor sign-in."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.admin_security_routes import build_admin_security_router
from app.gateways.http.admin_team_routes import build_admin_team_router
from app.gateways.http.business_security_routes import (
    build_business_security_router,
)
from app.gateways.http.mfa_routes import build_mfa_router
from app.gateways.http.session_routes import build_sessions_router
from app.gateways.http.support_access_routes import build_support_access_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_security_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    The key ring's view and its re-encryption run; two-factor sign-in,
    step-up and a business's two-factor requirement; the person's devices,
    the admin team and platform support's access to a business.
    """

    security = operators.security
    return [
        build_admin_security_router(
            get_encryption_keys_operator=security.get_encryption_keys_operator(),
            start_key_rotation_operator=security.start_key_rotation_operator(),
            current_user=current_user,
        ),
        build_mfa_router(
            verify_mfa_login_operator=security.verify_mfa_login_operator(),
            start_mfa_login_enrollment_operator=(
                security.start_mfa_login_enrollment_operator()
            ),
            get_account_security_operator=security.get_account_security_operator(),
            start_totp_enrollment_operator=security.start_totp_enrollment_operator(),
            confirm_totp_enrollment_operator=(
                security.confirm_totp_enrollment_operator()
            ),
            remove_totp_factor_operator=security.remove_totp_factor_operator(),
            regenerate_recovery_codes_operator=(
                security.regenerate_recovery_codes_operator()
            ),
            start_step_up_operator=security.start_step_up_operator(),
            verify_step_up_operator=security.verify_step_up_operator(),
            current_user=current_user,
        ),
        build_business_security_router(
            get_business_security_operator=security.get_business_security_operator(),
            update_business_security_operator=(
                security.update_business_security_operator()
            ),
            current_user=current_user,
        ),
        build_sessions_router(
            list_my_sessions_operator=security.list_my_sessions_operator(),
            revoke_session_operator=security.revoke_session_operator(),
            revoke_other_sessions_operator=security.revoke_other_sessions_operator(),
            current_user=current_user,
        ),
        build_admin_team_router(
            list_platform_admins_operator=security.list_platform_admins_operator(),
            add_platform_admin_operator=security.add_platform_admin_operator(),
            change_platform_admin_role_operator=(
                security.change_platform_admin_role_operator()
            ),
            remove_platform_admin_operator=security.remove_platform_admin_operator(),
            close_client_cabinet_operator=security.close_client_cabinet_operator(),
            current_user=current_user,
        ),
        build_support_access_router(
            get_support_access_operator=security.get_support_access_operator(),
            update_support_write_access_operator=(
                security.update_support_write_access_operator()
            ),
            end_support_access_operator=security.end_support_access_operator(),
            current_user=current_user,
        ),
    ]
