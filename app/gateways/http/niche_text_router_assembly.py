"""The router of the niche template editor (R17, migration 1221)."""

from fastapi import APIRouter

from app.containers.app import AppContainer
from app.containers.niche_texts.niche_text_operator_factories import (
    NicheTextOperatorFactories,
)
from app.gateways.http.admin_niche_text_routes import build_admin_niche_text_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_niche_text_routers(
    app_container: AppContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """/v1/admin/niche-templates, built from the context's typed root (ADR 0010)."""

    operators: NicheTextOperatorFactories = (
        app_container.use_cases.niche_text_root().operators
    )
    return [
        build_admin_niche_text_router(
            list_niche_texts_operator=operators.list_niche_texts(),
            get_niche_text_editor_operator=operators.get_niche_text_editor(),
            save_niche_text_draft_operator=operators.save_niche_text_draft(),
            discard_niche_text_draft_operator=operators.discard_niche_text_draft(),
            publish_niche_texts_operator=operators.publish_niche_texts(),
            revert_niche_texts_operator=operators.revert_niche_texts(),
            list_niche_text_versions_operator=operators.list_niche_text_versions(),
            current_user=current_user,
        )
    ]
