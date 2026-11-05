"""
Settings → Reviews (feedback after visits, the Google review link, the
statistics and the latest requests) and the public review link a customer
opens.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.paging_query import parse_page_request
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
    read_client_ip_address,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.feedback.feedback_requests import (
    FeedbackRequestPage,
    FeedbackRequestPageQuery,
)
from app.schemas.dto.feedback.review_links import ReviewLinkTarget, ReviewLinkVisit
from app.schemas.dto.feedback.review_settings import (
    ReviewSettingsQuery,
    ReviewSettingsRequest,
    ReviewSettingsView,
    UpdateReviewSettingsCommand,
)
from app.schemas.dto.feedback.review_stats import ReviewStatsQuery, ReviewStatsView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.feedback.constrained_strings import ReviewLinkToken
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.feedback.link_previews import is_link_preview_agent

B: str = "/v1/businesses/{business_id}"
REVIEW_LINK_PATH: str = "/v1/public/reviews/{token}"
# The redirect is personal (it counts one customer's visit): never cached,
# never indexed, and the review page does not learn where it came from.
REVIEW_LINK_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex",
    "Referrer-Policy": "no-referrer",
}

read_review_settings_body = build_json_body_dependency(ReviewSettingsRequest)


def build_review_router(
    *,
    current_user: CurrentUserDependency,
    get_settings: OperatorContract[ReviewSettingsQuery, ReviewSettingsView],
    update_settings: OperatorContract[UpdateReviewSettingsCommand, ReviewSettingsView],
    get_stats: OperatorContract[ReviewStatsQuery, ReviewStatsView],
    list_requests: OperatorContract[FeedbackRequestPageQuery, FeedbackRequestPage],
    open_review_link: OperatorContract[ReviewLinkVisit, ReviewLinkTarget],
) -> APIRouter:
    """
    Routes (Bearer auth; owners):
        GET {B}/review-settings        feedback after visits, the review link
        PUT {B}/review-settings        change them
        GET {B}/review-stats           the last 30 days in numbers
        GET {B}/feedback-requests      the visits asked about (paged)
    Public (no bearer token):
        GET /v1/public/reviews/{token} 302 to the business's review page
    """

    router = APIRouter(tags=["reviews"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    @router.get(f"{B}/review-settings")
    def get_review_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ReviewSettingsView:
        return get_settings.operate(
            ReviewSettingsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.put(
        f"{B}/review-settings",
        openapi_extra=describe_json_body(ReviewSettingsRequest),
    )
    def update_review_settings(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ReviewSettingsRequest, Depends(read_review_settings_body)],
    ) -> ReviewSettingsView:
        return update_settings.operate(
            UpdateReviewSettingsCommand(
                user_id=user_id, business_id=business(business_id), request=body
            )
        )

    @router.get(f"{B}/review-stats")
    def get_review_stats(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ReviewStatsView:
        return get_stats.operate(
            ReviewStatsQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.get(f"{B}/feedback-requests")
    def list_feedback_requests(
        business_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
        limit: Annotated[str | None, Query()] = None,
        cursor: Annotated[str | None, Query()] = None,
    ) -> FeedbackRequestPage:
        return list_requests.operate(
            FeedbackRequestPageQuery(
                user_id=user_id,
                business_id=business(business_id),
                page=parse_page_request(limit, cursor),
                client_ip_address=read_client_ip_address(request),
            )
        )

    @router.get(
        REVIEW_LINK_PATH,
        response_class=RedirectResponse,
        status_code=status.HTTP_302_FOUND,
        responses={
            status.HTTP_302_FOUND: {
                "description": "On to the business's review page (Location)."
            }
        },
    )
    def open_review(token: str, request: Request) -> RedirectResponse:
        target: ReviewLinkTarget = open_review_link.operate(
            ReviewLinkVisit(
                token=parse_review_token(token),
                is_link_preview=is_link_preview_agent(
                    request.headers.get("user-agent")
                ),
            )
        )
        return RedirectResponse(
            str(target.url),
            status_code=status.HTTP_302_FOUND,
            headers=REVIEW_LINK_HEADERS,
        )

    return router


def parse_review_token(raw_token: str) -> ReviewLinkToken:
    try:
        return ReviewLinkToken(raw_token.strip())
    except ValueError as error:
        raise NotFoundError("This review link is not available.") from error
