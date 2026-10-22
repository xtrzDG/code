"""
Routers of what follows a phone call: the telephony line, Settings → Calls
and the phone line's number the platform rents.
"""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.call_settings_routes import build_call_settings_router
from app.gateways.http.idempotency.idempotency_wiring import idempotency_of
from app.gateways.http.phone_number_routes import build_phone_number_router
from app.gateways.http.telephony_routes import build_telephony_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_call_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The telephony line's webhook, the owner's call settings, the phone line."""

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
        build_phone_number_router(
            current_user=current_user,
            get_phone_line_operator=calls.get_phone_line_operator(),
            search_phone_numbers_operator=calls.search_phone_numbers_operator(),
            rent_phone_number_operator=calls.rent_phone_number_operator(),
            request_phone_number_operator=calls.request_phone_number_operator(),
            cancel_phone_number_request_operator=(
                calls.cancel_phone_number_request_operator()
            ),
            idempotent=idempotency_of(operators, current_user),
        ),
    ]
