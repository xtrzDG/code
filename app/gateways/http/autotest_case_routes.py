"""The owner's own checks ("My checks"), which every autotest run plays."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.dto.assistants.autotest_cases import (
    AutotestCaseChanges,
    AutotestCaseCommand,
    AutotestCaseInput,
    AutotestCaseList,
    AutotestCaseView,
    CreateAutotestCaseCommand,
    ListAutotestCasesQuery,
    UpdateAutotestCaseCommand,
)
from app.schemas.typings.assistants.prefixed_id import AutotestCaseId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

read_case_body = build_json_body_dependency(AutotestCaseInput)
read_case_changes = build_json_body_dependency(AutotestCaseChanges)
CASES_PATH: str = "/v1/businesses/{business_id}/autotest-cases"


def build_autotest_case_router(
    current_user: CurrentUserDependency,
    list_cases: OperatorContract[ListAutotestCasesQuery, AutotestCaseList],
    create_case: OperatorContract[CreateAutotestCaseCommand, AutotestCaseView],
    update_case: OperatorContract[UpdateAutotestCaseCommand, AutotestCaseView],
    delete_case: OperatorContract[AutotestCaseCommand, None],
) -> APIRouter:
    """
    Routes (all require a bearer token; owners only):
        GET    /v1/businesses/{business_id}/autotest-cases
                                    the checks with their latest results
        POST   /v1/businesses/{business_id}/autotest-cases
                                    {question, expectation, expected_text?,
                                     language?, source?, source_*_id?}
        PATCH  /v1/businesses/{business_id}/autotest-cases/{case_id}
                                    {question?, expectation?, expected_text?,
                                     language?, is_active?}
        DELETE /v1/businesses/{business_id}/autotest-cases/{case_id}
    """

    router = APIRouter(tags=["assistants"], responses=standard_error_responses())

    def business(raw_id: str) -> BusinessId:
        return parse_path_identifier(raw_id, BusinessId, "Business")

    def case(raw_id: str) -> AutotestCaseId:
        return parse_path_identifier(raw_id, AutotestCaseId, "Check")

    @router.get(CASES_PATH)
    def list_autotest_cases(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> AutotestCaseList:
        return list_cases.operate(
            ListAutotestCasesQuery(user_id=user_id, business_id=business(business_id))
        )

    @router.post(
        CASES_PATH,
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(AutotestCaseInput),
    )
    def create_autotest_case(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AutotestCaseInput, Depends(read_case_body)],
    ) -> AutotestCaseView:
        return create_case.operate(
            CreateAutotestCaseCommand(
                user_id=user_id, business_id=business(business_id), case=body
            )
        )

    @router.patch(
        f"{CASES_PATH}/{{case_id}}",
        openapi_extra=describe_json_body(AutotestCaseChanges),
    )
    def update_autotest_case(
        business_id: str,
        case_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[AutotestCaseChanges, Depends(read_case_changes)],
    ) -> AutotestCaseView:
        return update_case.operate(
            UpdateAutotestCaseCommand(
                user_id=user_id,
                business_id=business(business_id),
                case_id=case(case_id),
                changes=body,
            )
        )

    @router.delete(f"{CASES_PATH}/{{case_id}}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_autotest_case(
        business_id: str,
        case_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        delete_case.operate(
            AutotestCaseCommand(
                user_id=user_id,
                business_id=business(business_id),
                case_id=case(case_id),
            )
        )

    return router
