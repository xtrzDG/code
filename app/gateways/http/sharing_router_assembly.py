"""Routers of sharing the assistant: links, address, hosted page, widget."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.public_booking_routes import build_public_booking_router
from app.gateways.http.public_chat_routes import build_public_chat_router
from app.gateways.http.sharing_routes import build_sharing_router
from app.gateways.http.spend_guard_router_assembly import widget_origin_guard_of
from app.gateways.http.user_authentication import CurrentUserDependency
from app.gateways.http.widget_handoff_routes import build_widget_handoff_router


def build_sharing_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    The routers that let customers reach a business without a website, and
    a guest's own booking page behind its manage link.
    """

    sharing = operators.sharing
    booking_links = operators.booking_links
    return [
        build_sharing_router(
            current_user=current_user,
            get_share_links_operator=sharing.get_share_links_operator(),
            set_public_slug_operator=sharing.set_public_slug_operator(),
        ),
        build_public_chat_router(sharing.hosted_chat_operator()),
        build_widget_handoff_router(
            sharing.widget_handoff_operator(), widget_origin_guard_of(operators)
        ),
        build_public_booking_router(
            view_operator=booking_links.managed_booking_operator(),
            calendar_operator=booking_links.managed_booking_calendar_operator(),
            slots_operator=booking_links.managed_booking_slots_operator(),
            cancel_operator=booking_links.cancel_managed_booking_operator(),
            reschedule_operator=booking_links.reschedule_managed_booking_operator(),
        ),
    ]
