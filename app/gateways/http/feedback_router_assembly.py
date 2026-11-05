"""Routers of the feedback after visits: Settings → Reviews and the review link."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.review_routes import build_review_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_feedback_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    feedback = operators.feedback
    return [
        build_review_router(
            current_user=current_user,
            get_settings=feedback.get_review_settings_operator(),
            update_settings=feedback.update_review_settings_operator(),
            get_stats=feedback.get_review_stats_operator(),
            list_requests=feedback.list_feedback_requests_operator(),
            open_review_link=feedback.open_review_link_operator(),
        )
    ]
