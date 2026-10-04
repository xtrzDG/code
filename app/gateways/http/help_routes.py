"""
The help center (public), the platform's support contacts (public) and
what the signed-in person has seen of the cabinet's guidance.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.help import (
    HelpArticleQuery,
    HelpArticleView,
    HelpCenterQuery,
    HelpCenterView,
    HelpSearchRequest,
    HelpSearchResults,
    SupportContactsQuery,
    SupportContactsView,
)
from app.schemas.dto.help_progress import (
    ChangelogReadBody,
    ChangelogReadCommand,
    CoachMarkSeenCommand,
    HelpProgressQuery,
    HelpProgressView,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.help.constrained_strings import (
    CoachMarkKey,
    HelpArticleSlug,
    HelpSearchText,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId

type HelpCenterOperator = OperatorContract[HelpCenterQuery, HelpCenterView]
type HelpArticleOperator = OperatorContract[HelpArticleQuery, HelpArticleView]
type SearchHelpOperator = OperatorContract[HelpSearchRequest, HelpSearchResults]
type SupportContactsOperator = OperatorContract[
    SupportContactsQuery, SupportContactsView
]
type HelpProgressOperator = OperatorContract[HelpProgressQuery, HelpProgressView]
type CoachMarkOperator = OperatorContract[CoachMarkSeenCommand, HelpProgressView]
type ResetCoachMarksOperator = OperatorContract[HelpProgressQuery, None]
type ChangelogReadOperator = OperatorContract[ChangelogReadCommand, HelpProgressView]

read_changelog_body = build_json_body_dependency(ChangelogReadBody)
# Help responses change only with a release: browsers and the cabinet's
# server may keep them a few minutes.
HELP_CACHE_CONTROL: str = "public, max-age=300"


def path_language(raw_language: str) -> LanguageTag:
    """The language segment of a help path; not a language tag is 404."""

    try:
        language: LanguageTag | None = parse_language_parameter(raw_language)
    except ValidationFailedError as error:
        raise NotFoundError("The help center has no such language.") from error
    if language is None:
        raise NotFoundError("The help center has no such language.")
    return language


def build_help_router(
    get_help_center_operator: HelpCenterOperator,
    get_help_article_operator: HelpArticleOperator,
    search_help_operator: SearchHelpOperator,
    get_support_contacts_operator: SupportContactsOperator,
    get_help_progress_operator: HelpProgressOperator,
    mark_coach_mark_seen_operator: CoachMarkOperator,
    reset_coach_marks_operator: ResetCoachMarksOperator,
    read_changelog_operator: ChangelogReadOperator,
    current_user: CurrentUserDependency,
) -> APIRouter:
    """
    Routes (the help center and the support contacts need no token):
        GET    /v1/help/{language}                 articles by topic
        GET    /v1/help/{language}/search?q=       matching articles, best first
        GET    /v1/help/{language}/{slug}          one article (Markdown)
        GET    /v1/support/contacts                WhatsApp, Telegram, e-mail
        GET    /v1/me/help                         coach marks seen, changelog read
        PUT    /v1/me/help/coach-marks/{key}       a coach mark was closed
        DELETE /v1/me/help/coach-marks             show the coach marks again (204)
        PUT    /v1/me/help/changelog               the newest entry read

    The language falls back to its base language, then English; the
    answer says which language it is in.
    """

    router = APIRouter(tags=["help"], responses=standard_error_responses())

    @router.get("/v1/help/{language}")
    def get_help_center(language: str, response: Response) -> HelpCenterView:
        response.headers["Cache-Control"] = HELP_CACHE_CONTROL
        return get_help_center_operator.operate(
            HelpCenterQuery(language=path_language(language))
        )

    @router.get("/v1/help/{language}/search")
    def search_help(language: str, q: str | None = None) -> HelpSearchResults:
        text: HelpSearchText | None = parse_optional(q, HelpSearchText, "q")
        if text is None:
            raise ValidationFailedError("Query parameter q is required.")
        return search_help_operator.operate(
            HelpSearchRequest(language=path_language(language), text=text)
        )

    @router.get("/v1/help/{language}/{slug}")
    def get_help_article(
        language: str, slug: str, response: Response
    ) -> HelpArticleView:
        response.headers["Cache-Control"] = HELP_CACHE_CONTROL
        return get_help_article_operator.operate(
            HelpArticleQuery(
                language=path_language(language),
                slug=parse_path_identifier(slug, HelpArticleSlug, "Help article"),
            )
        )

    @router.get("/v1/support/contacts")
    def get_support_contacts() -> SupportContactsView:
        return get_support_contacts_operator.operate(SupportContactsQuery())

    @router.get("/v1/me/help")
    def get_help_progress(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> HelpProgressView:
        return get_help_progress_operator.operate(HelpProgressQuery(user_id=user_id))

    @router.put("/v1/me/help/coach-marks/{key}")
    def mark_coach_mark_seen(
        key: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> HelpProgressView:
        return mark_coach_mark_seen_operator.operate(
            CoachMarkSeenCommand(
                user_id=user_id,
                key=parse_path_identifier(key, CoachMarkKey, "Coach mark"),
            )
        )

    @router.delete("/v1/me/help/coach-marks", status_code=status.HTTP_204_NO_CONTENT)
    def reset_coach_marks(
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        reset_coach_marks_operator.operate(HelpProgressQuery(user_id=user_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(
        "/v1/me/help/changelog", openapi_extra=describe_json_body(ChangelogReadBody)
    )
    def read_changelog(
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ChangelogReadBody, Depends(read_changelog_body)],
    ) -> HelpProgressView:
        return read_changelog_operator.operate(
            ChangelogReadCommand(user_id=user_id, body=body)
        )

    return router
