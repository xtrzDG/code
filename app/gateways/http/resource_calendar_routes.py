"""Knowledge → Resources → a resource's calendars (cabinet, bearer token)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.gateways.http.operations.business_access import BusinessAuthorizer
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    parse_path_identifier,
)
from app.gateways.http.user_authentication import CurrentUserDependency
from app.schemas.constants.calendar_sync import BusyTimeSource
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.dto.calendar_sync.calendar_commands import (
    AddIcalImportCommand,
    BookingSystemLinkRequest,
    GoogleCalendarLinkRequest,
    IcalExportCommand,
    IcalImportRequest,
    LinkBookingSystemCommand,
    LinkGoogleCalendarCommand,
    RemoveCalendarSourceCommand,
    ResourceCalendarQuery,
    SyncResourceCalendarCommand,
)
from app.schemas.dto.calendar_sync.resource_calendar import (
    IcalExportCreated,
    ResourceCalendarView,
)
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.users.prefixed_id import UserId

CALENDAR_PATH: str = "/v1/businesses/{business_id}/resources/{resource_id}/calendar"
OWNER: BusinessMemberRole = BusinessMemberRole.OWNER

read_google_body = build_json_body_dependency(GoogleCalendarLinkRequest)
read_ical_body = build_json_body_dependency(IcalImportRequest)
read_booking_system_body = build_json_body_dependency(BookingSystemLinkRequest)

type CalendarOperator[Input] = OperatorContract[Input, ResourceCalendarView]
type RemovalOperator[Input] = OperatorContract[Input, None]


def build_resource_calendar_router(
    *,
    current_user: CurrentUserDependency,
    authorize: BusinessAuthorizer,
    get_calendar: CalendarOperator[ResourceCalendarQuery],
    sync_calendar: CalendarOperator[SyncResourceCalendarCommand],
    link_google: CalendarOperator[LinkGoogleCalendarCommand],
    add_ical_import: CalendarOperator[AddIcalImportCommand],
    link_booking_system: CalendarOperator[LinkBookingSystemCommand],
    remove_source: RemovalOperator[RemoveCalendarSourceCommand],
    create_export: OperatorContract[IcalExportCommand, IcalExportCreated],
    remove_export: RemovalOperator[IcalExportCommand],
) -> APIRouter:
    """
    Routes of `CALENDAR_PATH` (owners and staff read and sync; owners change):
        GET    ...                      the resource's calendars
        POST   .../sync                 read every source now (2 s each)
        PUT    .../google               {calendar_id}; DELETE: unlink (204)
        POST   .../ical-imports         {url} (Airbnb, Booking.com, any feed)
        DELETE .../ical-imports/{id}    stop importing a feed (204)
        PUT    .../booking-system       {kind, external_resource_id, api_key}
        DELETE .../booking-system       unlink (204)
        POST   .../ical-export          a new export address, shown once (201)
        DELETE .../ical-export          switch the address off (204)
    """

    router = APIRouter(tags=["resources"], responses=standard_error_responses())

    def resource_of(
        user_id: UserId,
        business_id: str,
        resource_id: str,
        role: BusinessMemberRole | None,
    ) -> ResourceCalendarQuery:
        business = authorize(user_id, business_id, role)
        return ResourceCalendarQuery(
            business_id=business.id,
            resource_id=parse_path_identifier(resource_id, ResourceId, "Resource"),
        )

    @router.get(CALENDAR_PATH)
    def get_resource_calendar(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ResourceCalendarView:
        return get_calendar.operate(
            resource_of(user_id, business_id, resource_id, None)
        )

    @router.post(f"{CALENDAR_PATH}/sync")
    def sync_resource_calendar(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> ResourceCalendarView:
        query = resource_of(user_id, business_id, resource_id, None)
        return sync_calendar.operate(SyncResourceCalendarCommand(**query.model_dump()))

    @router.put(
        f"{CALENDAR_PATH}/google",
        openapi_extra=describe_json_body(GoogleCalendarLinkRequest),
    )
    def put_resource_google_calendar(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[GoogleCalendarLinkRequest, Depends(read_google_body)],
    ) -> ResourceCalendarView:
        query = resource_of(user_id, business_id, resource_id, OWNER)
        return link_google.operate(
            LinkGoogleCalendarCommand(
                **query.model_dump(), calendar_id=body.calendar_id, actor_id=user_id
            )
        )

    @router.post(
        f"{CALENDAR_PATH}/ical-imports",
        status_code=status.HTTP_201_CREATED,
        openapi_extra=describe_json_body(IcalImportRequest),
    )
    def post_resource_ical_import(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[IcalImportRequest, Depends(read_ical_body)],
    ) -> ResourceCalendarView:
        query = resource_of(user_id, business_id, resource_id, OWNER)
        return add_ical_import.operate(
            AddIcalImportCommand(**query.model_dump(), url=body.url, actor_id=user_id)
        )

    @router.put(
        f"{CALENDAR_PATH}/booking-system",
        openapi_extra=describe_json_body(BookingSystemLinkRequest),
    )
    def put_resource_booking_system(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
        body: Annotated[BookingSystemLinkRequest, Depends(read_booking_system_body)],
    ) -> ResourceCalendarView:
        query = resource_of(user_id, business_id, resource_id, OWNER)
        return link_booking_system.operate(
            LinkBookingSystemCommand(**query.model_dump(), link=body, actor_id=user_id)
        )

    def remove(
        user_id: UserId,
        business_id: str,
        resource_id: str,
        source: BusyTimeSource,
        feed_id: IcalImportFeedId | None = None,
    ) -> None:
        query = resource_of(user_id, business_id, resource_id, OWNER)
        remove_source.operate(
            RemoveCalendarSourceCommand(
                **query.model_dump(), source=source, feed_id=feed_id, actor_id=user_id
            )
        )

    @router.delete(f"{CALENDAR_PATH}/google", status_code=status.HTTP_204_NO_CONTENT)
    def delete_resource_google_calendar(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove(user_id, business_id, resource_id, BusyTimeSource.GOOGLE)

    @router.delete(
        f"{CALENDAR_PATH}/ical-imports/{{feed_id}}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_resource_ical_import(
        business_id: str,
        resource_id: str,
        feed_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove(
            user_id,
            business_id,
            resource_id,
            BusyTimeSource.ICAL,
            parse_path_identifier(feed_id, IcalImportFeedId, "Calendar feed"),
        )

    @router.delete(
        f"{CALENDAR_PATH}/booking-system", status_code=status.HTTP_204_NO_CONTENT
    )
    def delete_resource_booking_system(
        business_id: str,
        resource_id: str,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove(user_id, business_id, resource_id, BusyTimeSource.BOOKING_SYSTEM)

    def export_command(
        user_id: UserId, business_id: str, resource_id: str, request: Request
    ) -> IcalExportCommand:
        query = resource_of(user_id, business_id, resource_id, OWNER)
        return IcalExportCommand(
            **query.model_dump(),
            actor_id=user_id,
            public_base_url=PublicBaseUrl(str(request.base_url).rstrip("/")),
        )

    @router.post(f"{CALENDAR_PATH}/ical-export", status_code=status.HTTP_201_CREATED)
    def post_resource_ical_export(
        business_id: str,
        resource_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> IcalExportCreated:
        return create_export.operate(
            export_command(user_id, business_id, resource_id, request)
        )

    @router.delete(
        f"{CALENDAR_PATH}/ical-export", status_code=status.HTTP_204_NO_CONTENT
    )
    def delete_resource_ical_export(
        business_id: str,
        resource_id: str,
        request: Request,
        user_id: Annotated[UserId, Depends(current_user)],
    ) -> None:
        remove_export.operate(
            export_command(user_id, business_id, resource_id, request)
        )

    return router
