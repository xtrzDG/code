"""HTTP routes of bookable resources and schedule exceptions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.query_parsing import parse_boolean_text, parse_optional
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.resources import (
    CreateResourceCommand,
    CreateScheduleExceptionCommand,
    DeleteScheduleExceptionCommand,
    ResourceInput,
    ResourceList,
    ResourceListQuery,
    ResourcePatch,
    ResourceView,
    ScheduleExceptionDeletion,
    ScheduleExceptionInput,
    ScheduleExceptionList,
    ScheduleExceptionListQuery,
    ScheduleExceptionView,
    UpdateResourceCommand,
)
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId, ScheduleExceptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId

type BusinessAccessOperator = OperatorContract[BusinessAccessRequest, BusinessDocument]

read_resource_input = build_json_body_dependency(ResourceInput)
read_resource_patch = build_json_body_dependency(ResourcePatch)
read_schedule_exception_input = build_json_body_dependency(ScheduleExceptionInput)


def build_resource_router(
    current_user: CurrentUserDependency,
    business_access_operator: BusinessAccessOperator,
    list_resources_operator: OperatorContract[ResourceListQuery, ResourceList],
    create_resource_operator: OperatorContract[CreateResourceCommand, ResourceView],
    update_resource_operator: OperatorContract[UpdateResourceCommand, ResourceView],
    list_schedule_exceptions_operator: OperatorContract[
        ScheduleExceptionListQuery, ScheduleExceptionList
    ],
    create_schedule_exception_operator: OperatorContract[
        CreateScheduleExceptionCommand, ScheduleExceptionView
    ],
    delete_schedule_exception_operator: OperatorContract[
        DeleteScheduleExceptionCommand, ScheduleExceptionDeletion
    ],
) -> APIRouter:
    """
    Routes of resources (tables, rooms, masters, arenas, bays, cars) and of
    holidays and special-hours days.

    Owners and staff manage them. Resources are switched off with PATCH
    `is_active`; schedule exceptions are deleted. Dates are business-local
    "YYYY-MM-DD" and hours are local minutes of the day.
    """

    router: APIRouter = APIRouter(
        tags=["resources"], responses=standard_error_responses()
    )

    def authorize(user_id: UserId, raw_business_id: str) -> BusinessDocument:
        business_id: BusinessId = parse_path_identifier(
            raw_business_id,
            BusinessId,
            "Business",
        )
        return business_access_operator.operate(
            BusinessAccessRequest(user_id=user_id, business_id=business_id)
        )

    @router.get("/v1/businesses/{business_id}/resources")
    def list_resources(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        is_active: Annotated[str | None, Query()] = None,
    ) -> ResourceList:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_resources_operator.operate(
            ResourceListQuery(
                business_id=business.id,
                is_active=parse_optional(is_active, parse_boolean_text, "is_active"),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/resources",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(ResourceInput),
    )
    def create_resource(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        resource: Annotated[ResourceInput, Depends(read_resource_input)],
    ) -> ResourceView:
        business: BusinessDocument = authorize(user_id, business_id)
        return create_resource_operator.operate(
            CreateResourceCommand(
                business_id=business.id,
                resource=resource,
            )
        )

    @router.patch(
        "/v1/businesses/{business_id}/resources/{resource_id}",
        openapi_extra=describe_json_body(ResourcePatch),
    )
    def update_resource(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        patch: Annotated[ResourcePatch, Depends(read_resource_patch)],
    ) -> ResourceView:
        business: BusinessDocument = authorize(user_id, business_id)
        return update_resource_operator.operate(
            UpdateResourceCommand(
                business_id=business.id,
                resource_id=parse_path_identifier(resource_id, ResourceId, "Resource"),
                patch=patch,
            )
        )

    @router.get("/v1/businesses/{business_id}/schedule-exceptions")
    def list_schedule_exceptions(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        resource_id: Annotated[str | None, Query()] = None,
        from_date: Annotated[str | None, Query()] = None,
    ) -> ScheduleExceptionList:
        business: BusinessDocument = authorize(user_id, business_id)
        return list_schedule_exceptions_operator.operate(
            ScheduleExceptionListQuery(
                business_id=business.id,
                resource_id=parse_optional(resource_id, ResourceId, "resource_id"),
                from_date=parse_optional(from_date, LocalDate, "from_date"),
            )
        )

    @router.post(
        "/v1/businesses/{business_id}/schedule-exceptions",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(ScheduleExceptionInput),
    )
    def create_schedule_exception(
        business_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        exception: Annotated[
            ScheduleExceptionInput, Depends(read_schedule_exception_input)
        ],
    ) -> ScheduleExceptionView:
        business: BusinessDocument = authorize(user_id, business_id)
        return create_schedule_exception_operator.operate(
            CreateScheduleExceptionCommand(
                business_id=business.id,
                exception=exception,
            )
        )

    @router.delete(
        "/v1/businesses/{business_id}/schedule-exceptions/{exception_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_schedule_exception(
        business_id: str,
        exception_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        business: BusinessDocument = authorize(user_id, business_id)
        delete_schedule_exception_operator.operate(
            DeleteScheduleExceptionCommand(
                business_id=business.id,
                exception_id=parse_path_identifier(
                    exception_id,
                    ScheduleExceptionId,
                    "Schedule exception",
                ),
            )
        )

    return router
