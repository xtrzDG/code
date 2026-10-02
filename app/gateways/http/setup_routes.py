"""The guided setup: one-call creation, progress, skipped steps and milestones."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.language_negotiation import parse_language_parameter
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.setup import ActivationEventKind, SetupStepCode
from app.schemas.dto.businesses import (
    BusinessView,
    CreateBusinessCommand,
    CreateBusinessRequest,
)
from app.schemas.dto.setup.assistant_creation import AssistantCreatedView
from app.schemas.dto.setup.setup_progress import (
    ActivationMilestoneView,
    CelebrateMilestoneCommand,
    SetupQuery,
    SetupView,
    SkipSetupStepCommand,
)
from app.schemas.dto.setup.starter_answers import (
    StarterAnswersQuery,
    StarterAnswersView,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

SETUP_PATH: str = "/v1/businesses/{business_id}/setup"
SKIPPED_STEP_PATH: str = SETUP_PATH + "/skipped-steps/{step}"

read_create_assistant_body = build_json_body_dependency(CreateBusinessRequest)


def build_setup_router(
    current_user: CurrentUserDependency,
    create_business_operator: OperatorContract[CreateBusinessCommand, BusinessView],
    get_setup_progress_operator: OperatorContract[SetupQuery, SetupView],
    skip_setup_step_operator: OperatorContract[SkipSetupStepCommand, SetupView],
    celebrate_milestone_operator: OperatorContract[
        CelebrateMilestoneCommand, ActivationMilestoneView
    ],
    get_starter_answers_operator: OperatorContract[
        StarterAnswersQuery, StarterAnswersView
    ],
) -> APIRouter:
    """
    Routes (bearer token; reads for owners and staff, changes for owners
    except celebrating a milestone):
        POST   /v1/assistants
               "Create an AI assistant": the business with its country's
               defaults, its guided setup and its niche's starter answers
               (201)
        GET    /v1/businesses/{business_id}/setup
               the setup steps (business, offer, hours and bookings, staff
               contact, channels, test, launch), progress, next action,
               test-from-your-phone links, milestones and apply progress
        PUT    /v1/businesses/{business_id}/setup/skipped-steps/{step}
               skip an optional step (offer, channels, test)
        DELETE /v1/businesses/{business_id}/setup/skipped-steps/{step}
               bring a skipped step back (204)
        POST   /v1/businesses/{business_id}/setup/milestones/{kind}/celebrate
               the cabinet showed a milestone's celebration (once)

    Texts follow `?language=`, then the owner's language, then English.
    """

    router: APIRouter = APIRouter(tags=["setup"], responses=standard_error_responses())

    @router.post(
        "/v1/assistants",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(CreateBusinessRequest),
    )
    def create_assistant(
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[CreateBusinessRequest, Depends(read_create_assistant_body)],
    ) -> AssistantCreatedView:
        business: BusinessView = create_business_operator.operate(
            CreateBusinessCommand(user_id=user_id, details=body)
        )
        return AssistantCreatedView(
            business=business,
            setup=get_setup_progress_operator.operate(
                SetupQuery(user_id=user_id, business_id=business.id)
            ),
            starter_answers=get_starter_answers_operator.operate(
                StarterAnswersQuery(user_id=user_id, business_id=business.id)
            ),
        )

    @router.get(SETUP_PATH)
    def get_setup(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        language: Annotated[str | None, Query()] = None,
    ) -> SetupView:
        return get_setup_progress_operator.operate(
            SetupQuery(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                language=parse_language_parameter(language),
            )
        )

    @router.put(SKIPPED_STEP_PATH)
    def skip_setup_step(
        business_id: str,
        step: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SetupView:
        return skip_setup_step_operator.operate(
            build_skip_command(user_id, business_id, step, is_skipped=True)
        )

    @router.delete(SKIPPED_STEP_PATH, status_code=status.HTTP_204_NO_CONTENT)
    def unskip_setup_step(
        business_id: str,
        step: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        skip_setup_step_operator.operate(
            build_skip_command(user_id, business_id, step, is_skipped=False)
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(SETUP_PATH + "/milestones/{kind}/celebrate")
    def celebrate_milestone(
        business_id: str,
        kind: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ActivationMilestoneView:
        return celebrate_milestone_operator.operate(
            CelebrateMilestoneCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                kind=parse_path_identifier(kind, ActivationEventKind, "Milestone"),
            )
        )

    return router


def parse_business_id(raw_business_id: str) -> BusinessId:
    """Path segment -> BusinessId; malformed ids are reported as not found."""

    return parse_path_identifier(raw_business_id, BusinessId, "Business")


def build_skip_command(
    user_id: UserId,
    raw_business_id: str,
    raw_step: str,
    is_skipped: bool,
) -> SkipSetupStepCommand:
    return SkipSetupStepCommand(
        user_id=user_id,
        business_id=parse_business_id(raw_business_id),
        step=parse_path_identifier(raw_step, SetupStepCode, "Setup step"),
        is_skipped=is_skipped,
    )
