"""
Cabinet routes of where customers came from (Reports) and what they ask
about (the Overview card).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.value import ValuePeriod
from app.schemas.dto.value.conversation_topics import (
    ConversationTopicsQuery,
    ConversationTopicsView,
)
from app.schemas.dto.value.customer_sources import (
    CustomerSourcesQuery,
    CustomerSourcesView,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

B: str = "/v1/businesses/{business_id}"


def build_value_insight_router(
    *,
    current_user: CurrentUserDependency,
    get_sources: OperatorContract[CustomerSourcesQuery, CustomerSourcesView],
    get_topics: OperatorContract[ConversationTopicsQuery, ConversationTopicsView],
) -> APIRouter:
    """
    Routes (Bearer auth):
        GET {B}/value/sources   customers per source of a period (owners)
        GET {B}/value/topics    what customers ask about (owners and staff)
    """

    router = APIRouter(tags=["value"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(f"{B}/value/sources")
    def get_customer_sources(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        period: Annotated[str | None, Query()] = None,
        date_from: Annotated[str | None, Query(alias="from")] = None,
        date_to: Annotated[str | None, Query(alias="to")] = None,
    ) -> CustomerSourcesView:
        """
        Conversations, kept bookings, requests and their value per source
        (a link's tag, a QR code, an ad, the phone line). `period`: today,
        7d, 30d, 90d, last_week or last_month; or local dates `from` and
        `to`; neither: the last 30 days.
        """

        return get_sources.operate(
            CustomerSourcesQuery(
                user_id=user_id,
                business_id=business(business_id),
                period=parse_optional(period, ValuePeriod, "period"),
                date_from=parse_optional(date_from, LocalDate, "from"),
                date_to=parse_optional(date_to, LocalDate, "to"),
            )
        )

    @router.get(f"{B}/value/topics")
    def get_conversation_topics(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> ConversationTopicsView:
        """
        The topics of the last 30 days' first messages, grouped nightly,
        labelled in `?language=` (the cabinet's; else the owner's).
        """

        return get_topics.operate(
            ConversationTopicsQuery(
                user_id=user_id,
                business_id=business(business_id),
                language=parse_language_parameter(language),
            )
        )

    return router
