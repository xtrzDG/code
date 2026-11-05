"""The users, business and compliance routers over an accounts testbed."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.business_routes import build_business_router
from app.gateways.http.compliance_routes import build_compliance_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.http.users_routes import build_users_router
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from tests.users.accounts_compliance_use_cases import AccountsComplianceUseCases


def build_accounts_http_client(testbed: AccountsComplianceUseCases) -> TestClient:
    """FastAPI app with the three accounts routers over this testbed."""

    current_user = build_current_user_dependency(
        PipelineOperator(
            OrchestratorPipeline(UseCaseOrchestrator(testbed.authenticate_user))
        ),
        testbed.session_assurance,
    )
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_users_router(
            start_otp_login_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.start_otp_login))
            ),
            get_login_options_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.get_login_options))
            ),
            verify_otp_login_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.verify_otp_login))
            ),
            logout_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.logout))
            ),
            get_current_user_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.get_current_user))
            ),
            update_current_user_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.update_current_user))
            ),
            current_user=current_user,
        )
    )
    http_application.include_router(
        build_business_router(
            create_business_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.create_business))
            ),
            list_my_businesses_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.list_my_businesses))
            ),
            get_business_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.get_business))
            ),
            update_business_settings_operator=PipelineOperator(
                OrchestratorPipeline(
                    UseCaseOrchestrator(testbed.update_business_settings)
                )
            ),
            invite_staff_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.invite_staff))
            ),
            remove_member_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.remove_member))
            ),
            change_member_role_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.change_member_role))
            ),
            current_user=current_user,
        )
    )
    http_application.include_router(
        build_compliance_router(
            get_dpa_status_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.get_dpa_status))
            ),
            accept_dpa_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.accept_dpa))
            ),
            list_audit_log_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.list_audit_log))
            ),
            export_contact_data_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.export_contact_data))
            ),
            list_contacts_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.list_contacts))
            ),
            get_contact_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.get_contact))
            ),
            get_dpa_document_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.get_dpa_document))
            ),
            delete_contact_data_operator=PipelineOperator(
                OrchestratorPipeline(UseCaseOrchestrator(testbed.delete_contact_data))
            ),
            current_user=current_user,
        )
    )
    return TestClient(http_application)
