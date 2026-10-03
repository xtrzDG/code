"""The billing and admin routers over a billing testbed."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.admin_routes import build_admin_router
from app.gateways.http.billing_routes import build_billing_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.operators.pipeline_operator import PipelineOperator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from tests.billing.billing_fakes import TokenAuthenticationOperator, build_operator
from tests.billing.billing_use_cases import BillingUseCases


def build_billing_http_client(testbed: BillingUseCases) -> TestClient:
    current_user = build_current_user_dependency(
        TokenAuthenticationOperator(testbed.user_repo)
    )
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_billing_router(
            get_billing_overview_operator=build_operator(testbed.get_overview),
            start_trial_operator=build_operator(testbed.start_trial),
            change_plan_operator=build_operator(testbed.change_plan),
            cancel_subscription_operator=build_operator(testbed.cancel_subscription),
            start_checkout_operator=build_operator(testbed.start_checkout),
            subscribe_operator=PipelineOperator(
                OrchestratorPipeline(testbed.subscribe)
            ),
            payment_webhook_operator=build_operator(testbed.process_webhook),
            current_user=current_user,
        )
    )
    http_application.include_router(
        build_admin_router(
            list_clients_operator=build_operator(testbed.list_clients),
            get_client_health_operator=build_operator(testbed.get_client_health),
            open_client_cabinet_operator=build_operator(testbed.open_client_cabinet),
            current_user=current_user,
        )
    )
    return TestClient(http_application)
