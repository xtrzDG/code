"""The telephony and Settings → Calls routers over a channels testbed."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.call_settings_routes import build_call_settings_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.telephony_routes import build_telephony_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.orchestrators.voice.pbx_call_webhook_orchestrator import (
    PbxCallWebhookOrchestrator,
)
from app.use_cases.voice.call_settings.get_call_settings_use_case import (
    GetCallSettingsUseCase,
)
from app.use_cases.voice.call_settings.list_text_backs_use_case import (
    ListTextBacksUseCase,
)
from app.use_cases.voice.call_settings.update_call_settings_use_case import (
    UpdateCallSettingsUseCase,
)
from tests.channels.channels_http import wrap, wrap_use_case
from tests.channels.testbed import ChannelsTestbed


def build_calls_http_client(testbed: ChannelsTestbed) -> TestClient:
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_telephony_router(
            wrap(
                PbxCallWebhookOrchestrator(
                    testbed.read_pbx_missed_call, testbed.missed_calls
                )
            )
        )
    )
    http_application.include_router(
        build_call_settings_router(
            current_user=build_current_user_dependency(testbed.authentication),
            get_settings=wrap_use_case(
                GetCallSettingsUseCase(
                    testbed.authorize_business_access,
                    testbed.call_settings_repo,
                    testbed.channel_repo,
                    testbed.text_resolver,
                    testbed.sms_client,
                )
            ),
            update_settings=wrap_use_case(
                UpdateCallSettingsUseCase(
                    testbed.authorize_business_access,
                    testbed.call_settings_repo,
                    testbed.channel_repo,
                    testbed.audit_log_repo,
                    testbed.text_resolver,
                    testbed.sms_client,
                    testbed.wall_clock,
                )
            ),
            list_text_backs=wrap_use_case(
                ListTextBacksUseCase(
                    testbed.authorize_business_access,
                    testbed.missed_call_repo,
                    testbed.audit_log_repo,
                    testbed.wall_clock,
                )
            ),
        )
    )
    return TestClient(http_application)
