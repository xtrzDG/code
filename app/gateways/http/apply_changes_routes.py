"""'Apply changes': build, check and publish the assistant in one call."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import parse_path_identifier
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.setup.apply_changes import (
    ApplyChangesCommand,
    ApplyChangesQuery,
    ApplyChangesView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

APPLY_PATH: str = "/v1/businesses/{business_id}/assistant/apply"


def build_apply_changes_router(
    current_user: CurrentUserDependency,
    apply_changes_operator: OperatorContract[ApplyChangesCommand, ApplyChangesView],
    get_apply_changes_operator: OperatorContract[ApplyChangesQuery, ApplyChangesView],
) -> APIRouter:
    """
    Routes (bearer token):
        POST /v1/businesses/{business_id}/assistant/apply
             owners: build a version from the current profile and knowledge,
             check it in the background and publish it when the checks pass
             (202). Idempotent: while an apply is under way, or when the
             live version is up to date, the current one is returned.
        GET  /v1/businesses/{business_id}/assistant/apply
             owners and staff: its stage (building, checking, publishing,
             live, needs_attention), checks done of total, plain-language
             reasons with where to fix each, and whether changes are not
             live yet

    The first publish is the go-live: it starts the free trial when it is
    still due. Versions and autotests stay available under
    /assistant-versions for advanced use.
    """

    router: APIRouter = APIRouter(
        tags=["assistant"], responses=standard_error_responses()
    )

    @router.post(APPLY_PATH, status_code=status.HTTP_202_ACCEPTED)
    def apply_changes(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ApplyChangesView:
        return apply_changes_operator.operate(
            ApplyChangesCommand(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    @router.get(APPLY_PATH)
    def get_apply_changes(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> ApplyChangesView:
        return get_apply_changes_operator.operate(
            ApplyChangesQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                language=parse_language_parameter(language),
            )
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    """Path segment -> BusinessId; malformed ids are reported as not found."""

    return parse_path_identifier(raw_business_id, BusinessId, "Business")
