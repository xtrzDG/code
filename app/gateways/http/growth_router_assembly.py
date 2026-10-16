"""Routers of the revenue features: the waitlist, the return visits, deposits."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.deposit_routes import build_deposit_router
from app.gateways.http.return_visit_routes import build_return_visit_router
from app.gateways.http.user_authentication import CurrentUserDependency
from app.gateways.http.waitlist_routes import build_waitlist_router


def build_growth_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """Bookings → Waitlist, Bookings → Return visits, and the deposits."""

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
        build_deposit_router(
            current_user=current_user,
            get_settings=growth.get_deposit_settings_operator(),
            update_settings=growth.update_deposit_settings_operator(),
            add_link=growth.add_payment_link_operator(),
            remove_link=growth.remove_payment_link_operator(),
            set_policy=growth.set_deposit_policy_operator(),
            get_deposit=growth.get_deposit_request_operator(),
            mark_paid=growth.mark_deposit_paid_operator(),
            get_report=growth.get_deposit_report_operator(),
        ),
    ]
