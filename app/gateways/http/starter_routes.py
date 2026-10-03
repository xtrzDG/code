"""Starter answers of the niche and the profile autosave of the guided setup."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.profiles.business_profile import BusinessProfileView
from app.schemas.dto.setup.profile_patch import PatchProfileCommand, ProfilePatch
from app.schemas.dto.setup.starter_answers import (
    ApplyStarterAnswersCommand,
    ApplyStarterAnswersRequest,
    StarterAnswersApplied,
    StarterAnswersQuery,
    StarterAnswersView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

STARTER_ANSWERS_PATH: str = "/v1/businesses/{business_id}/setup/starter-answers"

read_apply_starter_body = build_json_body_dependency(
    ApplyStarterAnswersRequest, optional=True
)
read_profile_patch = build_json_body_dependency(ProfilePatch, optional=True)


def build_starter_router(
    current_user: CurrentUserDependency,
    get_starter_answers_operator: OperatorContract[
        StarterAnswersQuery, StarterAnswersView
    ],
    apply_starter_answers_operator: OperatorContract[
        ApplyStarterAnswersCommand, StarterAnswersApplied
    ],
    patch_profile_operator: OperatorContract[PatchProfileCommand, BusinessProfileView],
) -> APIRouter:
    """
    Routes (bearer token; reads for owners and staff, changes for owners):
        GET   /v1/businesses/{business_id}/setup/starter-answers
              the niche's suggestions for this business (hours over its
              country's working week, booking rules, a first resource,
              handoff and forbidden rules, tone, frequent questions, offer
              examples without prices) and which sections are still empty
        POST  /v1/businesses/{business_id}/setup/starter-answers/apply
              accept them in one call: only empty sections are filled
        PATCH /v1/businesses/{business_id}/profile
              autosave: change only the profile fields sent

    Texts follow `?language=` (or the body's `language`), then the owner's
    language, then English.
    """

    router: APIRouter = APIRouter(tags=["setup"], responses=standard_error_responses())

    @router.get(STARTER_ANSWERS_PATH)
    def get_starter_answers(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> StarterAnswersView:
        return get_starter_answers_operator.operate(
            StarterAnswersQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                language=parse_language_parameter(language),
            )
        )

    @router.post(
        STARTER_ANSWERS_PATH + "/apply",
        openapi_extra=describe_json_body(ApplyStarterAnswersRequest, optional=True),
    )
    def apply_starter_answers(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[ApplyStarterAnswersRequest, Depends(read_apply_starter_body)],
    ) -> StarterAnswersApplied:
        return apply_starter_answers_operator.operate(
            ApplyStarterAnswersCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
            )
        )

    @router.patch(
        "/v1/businesses/{business_id}/profile",
        openapi_extra=describe_json_body(ProfilePatch, optional=True),
    )
    def patch_profile(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        patch: Annotated[ProfilePatch, Depends(read_profile_patch)],
    ) -> BusinessProfileView:
        return patch_profile_operator.operate(
            PatchProfileCommand(
                business_id=parse_business_id(business_id),
                actor_id=user_id,
                patch=patch,
            )
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    """Path segment -> BusinessId; malformed ids are reported as not found."""

    return parse_path_identifier(raw_business_id, BusinessId, "Business")
