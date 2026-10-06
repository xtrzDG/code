"""Routers of the revenue features: the waitlist and the return visits."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.return_visit_routes import build_return_visit_router
from app.gateways.http.user_authentication import CurrentUserDependency
from app.gateways.http.waitlist_routes import build_waitlist_router


def build_growth_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """Bookings → Waitlist and Bookings → Return visits."""

    growth = operators.growth
    return [
        build_waitlist_router(
            current_user=current_user,
            list_waitlist=growth.list_waitlist_operator(),
            remove_entry=growth.remove_waitlist_entry_operator(),
            get_settings=growth.get_waitlist_settings_operator(),
            update_settings=growth.update_waitlist_settings_operator(),
        ),
        build_return_visit_router(
            current_user=current_user,
            get_settings=growth.get_campaign_settings_operator(),
            update_settings=growth.update_campaign_settings_operator(),
            list_messages=growth.list_campaign_messages_operator(),
        ),
    ]
