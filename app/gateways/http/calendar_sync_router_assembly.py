"""Routers of two-way availability: a resource's calendars, integrations, feeds."""

from fastapi import APIRouter

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.http.calendar_integration_routes import (
    build_calendar_integration_router,
)
from app.gateways.http.operations.business_access import (
    BusinessAuthorizer,
    build_business_authorizer,
)
from app.gateways.http.resource_calendar_routes import build_resource_calendar_router
from app.gateways.http.user_authentication import CurrentUserDependency


def build_calendar_sync_routers(
    operators: OperatorsContainer,
    current_user: CurrentUserDependency,
) -> list[APIRouter]:
    """Knowledge → Resources calendars, Settings → Integrations, iCal feeds."""

    calendars = operators.calendars
    authorize: BusinessAuthorizer = build_business_authorizer(
        operators.accounts.authorize_business_access_operator()
    )
    return [
        build_resource_calendar_router(
            current_user=current_user,
            authorize=authorize,
            get_calendar=calendars.get_resource_calendar_operator(),
            sync_calendar=calendars.sync_resource_calendar_operator(),
            link_google=calendars.link_google_calendar_operator(),
            add_ical_import=calendars.add_ical_import_operator(),
            link_booking_system=calendars.link_booking_system_operator(),
            remove_source=calendars.remove_calendar_source_operator(),
            create_export=calendars.create_ical_export_operator(),
            remove_export=calendars.remove_ical_export_operator(),
        ),
        build_calendar_integration_router(
            current_user=current_user,
            authorize=authorize,
            list_integrations=calendars.list_integrations_operator(),
            list_google_calendars=calendars.list_google_calendars_operator(),
            export_feed=calendars.export_resource_busy_times_operator(),
        ),
    ]
