"""Routers of billing: plans and payments, billing details and invoice PDFs."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.billing_document_routes import build_billing_document_router
from app.gateways.http.billing_lifecycle_routes import build_billing_lifecycle_router
from app.gateways.http.billing_routes import build_billing_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_billing_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The billing page, plan changes, checkout and the payment webhook; the
    billing details and the invoice and receipt PDFs; the cancel dialog's
    offers and the seasonal pause."""

    billing = operators.billing
    lifecycle = operators.lifecycle
    return [
        build_billing_router(
            get_billing_overview_operator=billing.get_billing_overview_operator(),
            start_trial_operator=billing.start_trial_operator(),
            change_plan_operator=billing.change_plan_operator(),
            cancel_subscription_operator=billing.cancel_subscription_operator(),
            start_checkout_operator=billing.start_checkout_operator(),
            subscribe_operator=billing.subscribe_operator(),
            payment_webhook_operator=billing.process_payment_webhook_operator(),
            current_user=current_user,
        ),
        build_billing_document_router(
            get_billing_profile_operator=billing.get_billing_profile_operator(),
            save_billing_profile_operator=billing.save_billing_profile_operator(),
            get_billing_document_operator=billing.get_billing_document_operator(),
            current_user=current_user,
        ),
        build_billing_lifecycle_router(
            get_subscription_lifecycle_operator=(
                lifecycle.get_subscription_lifecycle_operator()
            ),
            pause_subscription_operator=lifecycle.pause_subscription_operator(),
            resume_subscription_operator=lifecycle.resume_subscription_operator(),
            accept_retention_offer_operator=(
                lifecycle.accept_retention_offer_operator()
            ),
            current_user=current_user,
        ),
    ]
