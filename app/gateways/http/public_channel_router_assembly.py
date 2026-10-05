"""The public channel routes: the platforms' webhooks and the website widget."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.channel_routes import build_channel_router
from app.gateways.http.spend_guard_router_assembly import widget_origin_guard_of


def build_public_channel_router(operators: OperatorsContainer) -> APIRouter:
    """
    Webhooks (each authenticated by its platform) and the widget's routes,
    which answer only on websites the business allows.
    """

    channels = operators.channels
    return build_channel_router(
        telegram_webhook_operator=channels.telegram_webhook_operator(),
        meta_webhook_verification_operator=channels.verify_meta_webhook_operator(),
        meta_webhook_operator=channels.meta_webhook_operator(),
        platform_bot_webhook_operator=channels.handle_platform_bot_update_operator(),
        widget_config_operator=channels.get_widget_config_operator(),
        widget_message_operator=channels.widget_message_operator(),
        widget_messages_operator=channels.get_widget_messages_operator(),
        widget_origin_guard=widget_origin_guard_of(operators),
    )
