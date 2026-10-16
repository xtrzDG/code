"""Routers of the cabinet's Channels page: connecting and setting up channels."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.channel_settings_routes import build_channel_settings_router
from app.gateways.http.channel_setup_routes import build_channel_setup_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_channel_setup_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """Connected channels, the widget code, staff templates and token checks."""

    channels = operators.channels
    return [
        build_channel_settings_router(
            list_channels_operator=channels.list_channels_operator(),
            connect_channel_operator=channels.connect_channel_operator(),
            disable_channel_operator=channels.disable_channel_operator(),
            widget_snippet_operator=channels.get_widget_snippet_operator(),
            create_telegram_link_operator=channels.create_telegram_link_operator(),
            current_user=current_user,
            set_whatsapp_staff_template_operator=(
                channels.set_whatsapp_staff_template_operator()
            ),
        ),
        build_channel_setup_router(
            current_user=current_user,
            validate_telegram_token_operator=(
                channels.validate_telegram_token_operator()
            ),
            set_whatsapp_staff_templates_operator=(
                channels.set_whatsapp_staff_templates_operator()
            ),
        ),
    ]
