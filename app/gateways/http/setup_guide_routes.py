"""The guide after the launch: the phone check, the QR card, the finished guide."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.setup_routes import SETUP_PATH, parse_business_id
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.setup import SetupShareMark
from app.schemas.dto.setup.setup_guide import (
    DismissSetupGuideCommand,
    MarkSetupSharedCommand,
    SetupRemindersQuery,
    SetupRemindersRequest,
    SetupRemindersView,
    StartPhoneCheckCommand,
    UpdateSetupRemindersCommand,
)
from app.schemas.dto.setup.setup_progress import SetupView
from app.schemas.typings.setup.booleans import IsSetupGuideDismissed
from app.schemas.typings.users.prefixed_id import UserId

GUIDE_DISMISSAL_PATH: str = SETUP_PATH + "/guide-dismissal"
REMINDERS_PATH: str = SETUP_PATH + "/reminders"

read_reminders_body = build_json_body_dependency(SetupRemindersRequest)


def build_setup_guide_router(
    current_user: CurrentUserDependency,
    start_phone_check_operator: OperatorContract[StartPhoneCheckCommand, SetupView],
    mark_setup_shared_operator: OperatorContract[MarkSetupSharedCommand, None],
    dismiss_setup_guide_operator: OperatorContract[DismissSetupGuideCommand, SetupView],
    get_setup_reminders_operator: OperatorContract[
        SetupRemindersQuery, SetupRemindersView
    ],
    update_setup_reminders_operator: OperatorContract[
        UpdateSetupRemindersCommand, SetupRemindersView
    ],
) -> APIRouter:
    """
    Routes (bearer token; owners and staff unless noted):
        POST   /v1/businesses/{business_id}/setup/phone-check
               "Try it from your phone" is open: a real conversation that
               starts within half an hour counts as the owner's own test
        POST   /v1/businesses/{business_id}/setup/share-marks/{mark}
               the QR card was printed or saved (204)
        PUT    /v1/businesses/{business_id}/setup/guide-dismissal
               put the finished guide away (owners; 409 while unfinished)
        DELETE /v1/businesses/{business_id}/setup/guide-dismissal
               bring it back (owners; 204)
        GET    /v1/businesses/{business_id}/setup/reminders
        PUT    /v1/businesses/{business_id}/setup/reminders
               the activation reminders on or off (owners)
    """

    router: APIRouter = APIRouter(tags=["setup"], responses=standard_error_responses())

    @router.post(SETUP_PATH + "/phone-check")
    def start_phone_check(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SetupView:
        return start_phone_check_operator.operate(
            StartPhoneCheckCommand(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    @router.post(
        SETUP_PATH + "/share-marks/{mark}", status_code=status.HTTP_204_NO_CONTENT
    )
    def mark_shared(
        business_id: str,
        mark: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        mark_setup_shared_operator.operate(
            MarkSetupSharedCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                mark=parse_path_identifier(mark, SetupShareMark, "Share mark"),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.put(GUIDE_DISMISSAL_PATH)
    def dismiss_guide(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SetupView:
        return dismiss_setup_guide_operator.operate(
            DismissSetupGuideCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                is_dismissed=IsSetupGuideDismissed(True),
            )
        )

    @router.delete(GUIDE_DISMISSAL_PATH, status_code=status.HTTP_204_NO_CONTENT)
    def bring_guide_back(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> Response:
        dismiss_setup_guide_operator.operate(
            DismissSetupGuideCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                is_dismissed=IsSetupGuideDismissed(False),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.get(REMINDERS_PATH)
    def get_reminders(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> SetupRemindersView:
        return get_setup_reminders_operator.operate(
            SetupRemindersQuery(
                user_id=user_id, business_id=parse_business_id(business_id)
            )
        )

    @router.put(REMINDERS_PATH, openapi_extra=describe_json_body(SetupRemindersRequest))
    def update_reminders(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[SetupRemindersRequest, Depends(read_reminders_body)],
    ) -> SetupRemindersView:
        return update_setup_reminders_operator.operate(
            UpdateSetupRemindersCommand(
                user_id=user_id,
                business_id=parse_business_id(business_id),
                request=body,
            )
        )

    return router
