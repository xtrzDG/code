"""Routers of what follows a phone call: the telephony line and Settings → Calls."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.call_settings_routes import build_call_settings_router
from app.gateways.http.telephony_routes import build_telephony_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_call_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The telephony line's webhook and the owner's call settings."""

    calls = operators.calls
    return [
        build_telephony_router(
            pbx_call_webhook_operator=calls.pbx_call_webhook_operator()
        ),
        build_call_settings_router(
            current_user=current_user,
            get_settings=calls.get_call_settings_operator(),
            update_settings=calls.update_call_settings_operator(),
            list_text_backs=calls.list_text_backs_operator(),
        ),
    ]
