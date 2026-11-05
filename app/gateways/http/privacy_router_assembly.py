"""
Routers of the exports of a business's data (CSV tables, the full export)
and of its retention settings.
"""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.business_export_routes import build_business_export_router
from app.gateways.http.export_routes import build_export_router
from app.gateways.http.privacy_settings_routes import build_privacy_settings_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_privacy_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    privacy = operators.privacy
    return [
        build_export_router(
            current_user=current_user,
            start_csv_export=privacy.start_csv_export_operator(),
            read_csv_export_page=privacy.read_csv_export_page_operator(),
        ),
        build_business_export_router(
            current_user=current_user,
            start_export=privacy.start_business_export_operator(),
            list_exports=privacy.list_business_exports_operator(),
            create_download_link=privacy.create_export_download_link_operator(),
            download_export=privacy.download_business_export_operator(),
        ),
        build_privacy_settings_router(
            current_user=current_user,
            get_settings=privacy.get_privacy_settings_operator(),
            update_settings=privacy.update_privacy_settings_operator(),
        ),
    ]
