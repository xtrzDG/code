"""The channel, channel settings and voice routers over a channels testbed."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.gateways.http.channel_routes import build_channel_router
from app.gateways.http.channel_settings_routes import build_channel_settings_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.gateways.http.voice_routes import build_voice_router
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.channels.channel_webhook_orchestrator import (
    ChannelWebhookOrchestrator,
)
from app.orchestrators.channels.post_call_webhook_orchestrator import (
    PostCallWebhookOrchestrator,
)
from app.orchestrators.channels.voice_tool_webhook_orchestrator import (
    VoiceToolWebhookOrchestrator,
)
from app.orchestrators.channels.widget_message_orchestrator import (
    WidgetMessageOrchestrator,
)
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.registries.billing.plan_registry import PlanRegistry
from app.use_cases.channels.accept_widget_message_use_case import (
    AcceptWidgetMessageUseCase,
)
from app.use_cases.channels.build_widget_reply_use_case import BuildWidgetReplyUseCase
from app.use_cases.channels.get_widget_config_use_case import GetWidgetConfigUseCase
from app.use_cases.channels.get_widget_messages_use_case import GetWidgetMessagesUseCase
from app.use_cases.channels.get_widget_snippet_use_case import GetWidgetSnippetUseCase
from app.use_cases.channels.verify_meta_webhook_use_case import VerifyMetaWebhookUseCase
from app.use_cases.voice.authenticate_post_call_use_case import (
    AuthenticatePostCallUseCase,
)
from app.use_cases.voice.authenticate_voice_tool_call_use_case import (
    AuthenticateVoiceToolCallUseCase,
)
from app.use_cases.voice.start_voice_call_use_case import StartVoiceCallUseCase
from tests.channels.channels_use_cases import ChannelsUseCases


def wrap[InputData, OutputData](
    orchestrator: OrchestratorContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    """Operator -> pipeline -> the given orchestrator (the generic chain)."""

    return PipelineOperator(OrchestratorPipeline(orchestrator))


def wrap_use_case[InputData, OutputData](
    use_case: UseCaseContract[InputData, OutputData],
) -> PipelineOperator[InputData, OutputData]:
    """Operator -> pipeline -> orchestrator -> the given use case."""

    return PipelineOperator(OrchestratorPipeline(UseCaseOrchestrator(use_case)))


def build_channels_http_client(testbed: ChannelsUseCases) -> TestClient:
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_channel_router(
            telegram_webhook_operator=wrap(
                ChannelWebhookOrchestrator(
                    testbed.receive_telegram_webhook,
                    testbed.pipeline,
                    testbed.deliver_reply,
                )
            ),
            meta_webhook_verification_operator=wrap_use_case(
                VerifyMetaWebhookUseCase(testbed.settings)
            ),
            meta_webhook_operator=wrap(
                ChannelWebhookOrchestrator(
                    testbed.receive_meta_webhook,
                    testbed.pipeline,
                    testbed.deliver_reply,
                )
            ),
            platform_bot_webhook_operator=wrap_use_case(
                testbed.handle_platform_bot_update
            ),
            widget_config_operator=wrap_use_case(
                GetWidgetConfigUseCase(
                    testbed.business_repo,
                    testbed.channel_repo,
                    testbed.assistant_version_repo,
                    testbed.language_registry,
                )
            ),
            widget_message_operator=wrap(
                WidgetMessageOrchestrator(
                    AcceptWidgetMessageUseCase(
                        testbed.business_repo,
                        testbed.channel_repo,
                        testbed.widget_rate_limits,
                        testbed.wall_clock,
                    ),
                    testbed.pipeline,
                    BuildWidgetReplyUseCase(
                        testbed.message_repo, testbed.language_registry
                    ),
                )
            ),
            widget_messages_operator=wrap_use_case(
                GetWidgetMessagesUseCase(
                    testbed.business_repo,
                    testbed.channel_repo,
                    testbed.conversation_repo,
                    testbed.message_repo,
                    testbed.language_registry,
                    testbed.widget_rate_limits,
                    testbed.wall_clock,
                )
            ),
        )
    )
    http_application.include_router(
        build_channel_settings_router(
            list_channels_operator=wrap_use_case(testbed.list_channels),
            connect_channel_operator=wrap_use_case(testbed.connect_channel),
            disable_channel_operator=wrap_use_case(testbed.disable_channel),
            widget_snippet_operator=wrap_use_case(
                GetWidgetSnippetUseCase(
                    testbed.authorize_business_access, testbed.settings
                )
            ),
            create_telegram_link_operator=wrap_use_case(testbed.create_telegram_link),
            current_user=build_current_user_dependency(testbed.authentication),
            set_whatsapp_staff_template_operator=wrap_use_case(
                testbed.set_whatsapp_staff_template
            ),
        )
    )
    http_application.include_router(
        build_voice_router(
            voice_tool_operator=wrap(
                VoiceToolWebhookOrchestrator(
                    AuthenticateVoiceToolCallUseCase(
                        testbed.business_repo,
                        testbed.voice_webhook_adapter,
                        testbed.phone_number_parser,
                        testbed.settings,
                    ),
                    testbed.voice_tool_orchestrator,
                )
            ),
            call_initiation_operator=wrap_use_case(
                StartVoiceCallUseCase(
                    testbed.business_repo,
                    testbed.assistant_version_repo,
                    testbed.channel_repo,
                    PlanRegistry(),
                    testbed.profile_repo,
                    testbed.exception_repo,
                    testbed.contact_repo,
                    testbed.booking_repo,
                    testbed.resource_repo,
                    testbed.wall_clock,
                    testbed.voice_webhook_adapter,
                    testbed.phone_number_parser,
                    testbed.call_greeting,
                    testbed.settings,
                )
            ),
            post_call_operator=wrap(
                PostCallWebhookOrchestrator(
                    AuthenticatePostCallUseCase(
                        testbed.voice_webhook_adapter, testbed.wall_clock
                    ),
                    testbed.record_finished_call,
                    testbed.send_call_confirmation,
                )
            ),
        )
    )
    return TestClient(http_application)
