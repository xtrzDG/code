"""The public channel routes: the platforms' webhooks and the website widget."""

from fastapi import APIRouter

from app.containers.app import AppContainer
from app.gateways.http.channel_routes import build_channel_router
from app.gateways.http.spend_guard_router_assembly import widget_origin_guard_of
from app.gateways.http.widget_event_routes import build_widget_event_router


def build_public_channel_router(app_container: AppContainer) -> APIRouter:
    """
    Webhooks (each authenticated by its platform) and the widget's routes,
    which answer only on websites the business allows: its configuration,
    messages and its visitors' live stream.
    """

    operators = app_container.operators
    channels = operators.channels
    router = APIRouter()
    router.include_router(
        build_channel_router(
            telegram_webhook_operator=channels.telegram_webhook_operator(),
            meta_webhook_verification_operator=channels.verify_meta_webhook_operator(),
            meta_webhook_operator=channels.meta_webhook_operator(),
            platform_bot_webhook_operator=channels.handle_platform_bot_update_operator(),
            widget_config_operator=channels.get_widget_config_operator(),
            widget_message_operator=channels.widget_message_operator(),
            widget_messages_operator=channels.get_widget_messages_operator(),
            widget_origin_guard=widget_origin_guard_of(operators),
        )
    )
    router.include_router(
        build_widget_event_router(
            open_widget_stream_operator=operators.sharing.open_widget_stream_operator(),
            read_widget_stream_message_operator=(
                operators.sharing.read_widget_stream_message_operator()
            ),
            stream_facilitator=app_container.facilitators.widget_stream_facilitator(),
            limits=app_container.facilitators.live.widget_stream_limits(),
            widget_origin_guard=widget_origin_guard_of(operators),
        )
    )
    return router
