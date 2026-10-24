"""Routers of the help center, the guidance each person saw and the status page."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.help_routes import build_help_router
from app.gateways.http.platform_status_routes import build_platform_status_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_help_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    /v1/help, /v1/support, /v1/me/help, /v1/platform/status and
    /v1/admin/announcements.
    """

    platform_ops = operators.platform_ops
    return [
        build_help_router(
            get_help_center_operator=platform_ops.get_help_center_operator(),
            get_help_article_operator=platform_ops.get_help_article_operator(),
            search_help_operator=platform_ops.search_help_operator(),
            get_support_contacts_operator=platform_ops.get_support_contacts_operator(),
            get_help_progress_operator=platform_ops.get_help_progress_operator(),
            mark_coach_mark_seen_operator=platform_ops.mark_coach_mark_seen_operator(),
            reset_coach_marks_operator=platform_ops.reset_coach_marks_operator(),
            read_changelog_operator=platform_ops.read_changelog_operator(),
            current_user=current_user,
        ),
        build_platform_status_router(
            get_platform_status_operator=platform_ops.get_platform_status_operator(),
            create_announcement_operator=platform_ops.create_announcement_operator(),
            update_announcement_operator=platform_ops.update_announcement_operator(),
            list_announcements_operator=platform_ops.list_announcements_operator(),
            current_user=current_user,
        ),
    ]
