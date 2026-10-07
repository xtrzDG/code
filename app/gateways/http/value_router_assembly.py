"""Router of what the assistant is worth: value, average check, reports."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.user_authentication import CurrentUserDependency
from app.gateways.http.value_insight_routes import build_value_insight_router
from app.gateways.http.value_routes import build_value_router


def build_value_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """
    The value of a period, the average check, digests, reports, today;
    customer sources and topics.
    """

    value = operators.value
    return [
        build_value_router(
            current_user=current_user,
            get_value=value.get_business_value_operator(),
            get_settings=value.get_value_settings_operator(),
            update_settings=value.update_value_settings_operator(),
            get_preferences=value.get_digest_preferences_operator(),
            update_preferences=value.update_digest_preferences_operator(),
            list_reports=value.list_value_reports_operator(),
            get_report=value.get_value_report_operator(),
            get_today_queue=value.get_today_queue_operator(),
        ),
        build_value_insight_router(
            current_user=current_user,
            get_sources=value.get_customer_sources_operator(),
            get_topics=value.get_conversation_topics_operator(),
        ),
    ]
