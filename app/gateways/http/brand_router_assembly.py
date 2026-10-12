"""Routers of brands (1192): the brand and its locations, its team, its knowledge."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.brand_knowledge_routes import build_brand_knowledge_router
from app.gateways.http.brand_routes import build_brand_router
from app.gateways.http.brand_team_routes import build_brand_team_router
from app.gateways.http.idempotency.idempotency_wiring import idempotency_of
from app.gateways.http.user_authentication import CurrentUserDependency


def build_brand_routers(
    operators: OperatorsContainer, current_user: CurrentUserDependency
) -> list[APIRouter]:
    brands = operators.brands
    return [
        build_brand_router(
            current_user=current_user,
            idempotent=idempotency_of(operators, current_user),
            list_brands=brands.list_my_brands_operator(),
            get_brand=brands.get_brand_operator(),
            create_brand=brands.create_brand_operator(),
            rename_brand=brands.rename_brand_operator(),
            delete_brand=brands.delete_brand_operator(),
            get_dashboard=brands.get_brand_dashboard_operator(),
            add_location=brands.add_brand_location_operator(),
            remove_location=brands.remove_brand_location_operator(),
            clone_location=brands.clone_brand_location_operator(),
        ),
        build_brand_team_router(
            current_user=current_user,
            invite_member=brands.invite_brand_member_operator(),
            change_member=brands.change_brand_member_operator(),
            remove_member=brands.remove_brand_member_operator(),
        ),
        build_brand_knowledge_router(
            current_user=current_user,
            list_items=brands.list_brand_knowledge_operator(),
            create_item=brands.create_brand_knowledge_item_operator(),
            update_item=brands.update_brand_knowledge_item_operator(),
            delete_item=brands.delete_brand_knowledge_item_operator(),
            override_item=brands.override_brand_knowledge_operator(),
            leave_brand=brands.leave_brand_operator(),
        ),
    ]
