"""Routers of the customer memory: Settings → General's switch."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.assistant_settings_routes import (
    build_assistant_settings_router,
)
from app.gateways.http.user_authentication import CurrentUserDependency


def build_memory_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """The routers of how the assistant remembers returning customers."""

    memory = operators.memory
    return [
        build_assistant_settings_router(
            current_user=current_user,
            get_assistant_settings_operator=memory.get_assistant_settings_operator(),
            update_assistant_settings_operator=(
                memory.update_assistant_settings_operator()
            ),
        )
    ]
