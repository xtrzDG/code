from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import (
    IcalExportFeedDocument,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.calendar_commands import IcalExportCommand
from app.schemas.dto.calendar_sync.resource_calendar import IcalExportCreated
from app.schemas.typings.calendar_sync.constrained_strings import (
    IcalExportTokenHash,
    IcalExportUrl,
)
from app.schemas.typings.calendar_sync.strings import IcalExportToken
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges
from app.use_cases.calendar_sync.calendar_refusals import calendar_refusal
from app.utilities.calendar_sync.calendar_sync_keys import (
    generate_export_token,
    hash_export_token,
)

EXPORT_PATH: str = "/v1/public/ical/{token}.ics"


class CreateIcalExportUseCase(UseCaseContract[IcalExportCommand, IcalExportCreated]):
    """
    Owners make the resource's export address: its bookings (and the busy
    times of its Google calendar and booking system) as an iCal feed to
    paste into Airbnb, Booking.com or any calendar. The address carries a
    random token shown this once (only its hash is stored); made again,
    the old address stops working at once. Audited.
    """

    def __init__(
        self, changes: CalendarChanges, app_base_url: PublicBaseUrl | None
    ) -> None:
        self._changes: CalendarChanges = changes
        self._app_base_url: PublicBaseUrl | None = app_base_url

    def run(self, input_data: IcalExportCommand) -> IcalExportCreated:
        base_url: PublicBaseUrl | None = (
            self._app_base_url or input_data.public_base_url
        )
        if base_url is None:
            raise calendar_refusal(
                "public_address_missing",
                "This server has no public address (APP_BASE_URL) for the feed.",
            )

        reader = self._changes.reader
        resource: ResourceDocument = reader.resource(
            input_data.business_id, input_data.resource_id
        )
        now: Microseconds = reader.wall_clock.now_unix()
        token: IcalExportToken = generate_export_token()
        feed = IcalExportFeedDocument(
            business_id=resource.business_id,
            resource_id=resource.id,
            token_hash=hash_export_token(token),
            created_at=now,
            updated_at=now,
        )
        reader.export_feed_repo.add(feed)
        replaced: list[IcalExportTokenHash] = []

        def point_to_feed(
            link: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument:
            replaced.clear()
            if link.ical_export_token_hash is not None:
                replaced.append(link.ical_export_token_hash)
            link.ical_export_id = feed.id
            link.ical_export_token_hash = feed.token_hash
            link.ical_export_created_at = now
            link.updated_at = now
            return link

        self._changes.change(resource, point_to_feed, now)
        for old_hash in replaced:
            reader.export_feed_repo.remove(resource.business_id, old_hash)
        self._changes.audit(resource, input_data.actor_id, AuditAction.CREATE, now)
        return IcalExportCreated(
            url=IcalExportUrl(
                str(base_url).rstrip("/") + EXPORT_PATH.format(token=token)
            ),
            calendar=reader.view_of(resource),
        )
