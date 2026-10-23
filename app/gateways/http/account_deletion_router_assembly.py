"""Routers of closing businesses and deleting accounts (R15, migration 1220)."""

from fastapi import APIRouter

from app.containers.account_deletion.account_deletion_operator_factories import (
    AccountDeletionOperatorFactories,
)
from app.containers.app import AppContainer
from app.gateways.http.account_deletion_routes import build_account_deletion_router
from app.gateways.http.business_closure_routes import build_business_closure_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_account_deletion_routers(
    app_container: AppContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    A business's closure (Settings → Business, the countdown banner) and a
    person's account deletion and certificates (Account), built from the
    context's typed root (ADR 0010).
    """

    operators: AccountDeletionOperatorFactories = (
        app_container.use_cases.account_deletion_root().operators
    )
    return [
        build_business_closure_router(
            get_business_closure_operator=operators.get_business_closure(),
            close_business_operator=operators.close_business(),
            cancel_business_closure_operator=operators.cancel_business_closure(),
            current_user=current_user,
        ),
        build_account_deletion_router(
            delete_current_user_operator=operators.delete_current_user(),
            list_business_deletions_operator=operators.list_business_deletions(),
            get_deletion_certificate_operator=operators.get_deletion_certificate(),
            current_user=current_user,
        ),
    ]
