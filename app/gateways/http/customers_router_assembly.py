"""Routers of Customers (the card, segments, settings) and the cabinet's search."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.customer_routes import build_customer_router
from app.gateways.http.customer_segment_routes import build_customer_segment_router
from app.gateways.http.search_routes import build_search_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_customer_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    customers = operators.customers
    return [
        build_customer_router(
            current_user=current_user,
            change_card=customers.change_customer_card_operator(),
            change_blocking=customers.change_customer_blocking_operator(),
            get_standing=customers.get_contact_standing_operator(),
            get_settings=customers.get_customer_settings_operator(),
            update_settings=customers.update_customer_settings_operator(),
        ),
        build_customer_segment_router(
            current_user=current_user,
            list_segments=customers.list_segments_operator(),
            create_segment=customers.create_segment_operator(),
            update_segment=customers.update_segment_operator(),
            delete_segment=customers.delete_segment_operator(),
            list_members=customers.list_segment_members_operator(),
            preview_segment=customers.preview_segment_operator(),
            start_export=customers.start_segment_export_operator(),
            read_export_page=customers.read_segment_export_page_operator(),
        ),
        build_search_router(
            current_user=current_user, search=customers.search_business_operator()
        ),
    ]
