from typed_time_provider import Microseconds

from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.calendar_sync import (
    IcalImportFeed,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.calendar_sync.calendar_commands import AddIcalImportCommand
from app.schemas.dto.calendar_sync.resource_calendar import ResourceCalendarView
from app.schemas.typings.calendar_sync.prefixed_id import IcalImportFeedId
from app.schemas.typings.channels.strings import ChannelSecret
from app.use_cases.calendar_sync.calendar_changes import CalendarChanges, due_now
from app.use_cases.calendar_sync.calendar_refusals import calendar_refusal
from app.utilities.calendar_sync.feed_addresses import feed_host, fetchable_feed_url

# Airbnb, Booking.com, Vrbo and a couple more channels per unit.
MAX_FEEDS_PER_RESOURCE: int = 5


class AddIcalImportUseCase(UseCaseContract[AddIcalImportCommand, ResourceCalendarView]):
    """
    Owners import an iCal feed into a resource (Airbnb, Booking.com, Vrbo,
    a public calendar): its reservations and closed days block the
    resource. The address is vetted (public https only), stored encrypted
    and never shown again; the cabinet sees its host. At most five feeds
    per resource, each address once. Read right away (2 s); audited.
    """

    def __init__(
        self, changes: CalendarChanges, secret_cipher: SecretCipherAdapterContract
    ) -> None:
        self._changes: CalendarChanges = changes
        self._secret_cipher: SecretCipherAdapterContract = secret_cipher

    def run(self, input_data: AddIcalImportCommand) -> ResourceCalendarView:
        reader = self._changes.reader
        resource: ResourceDocument = reader.resource(
            input_data.business_id, input_data.resource_id
        )
        self._changes.busy_time_sync.vet_feed_address(input_data.url)
        address: str = str(fetchable_feed_url(str(input_data.url)))
        now: Microseconds = reader.wall_clock.now_unix()
        feed = IcalImportFeed(
            feed_id=IcalImportFeedId(),
            encrypted_url=self._secret_cipher.encrypt(ChannelSecret(address)),
            host=feed_host(input_data.url),
            added_at=now,
        )

        def add_feed(
            link: ResourceCalendarLinkDocument,
        ) -> ResourceCalendarLinkDocument:
            if any(self._address_of(known) == address for known in link.ical_imports):
                raise calendar_refusal(
                    "feed_already_imported", "This calendar is imported already."
                )
            if len(link.ical_imports) >= MAX_FEEDS_PER_RESOURCE:
                raise calendar_refusal(
                    "feed_limit",
                    f"A resource imports at most {MAX_FEEDS_PER_RESOURCE} calendars.",
                )

            link.ical_imports.append(feed)
            due_now(link, now)
            return link

        self._changes.change(resource, add_feed, now)
        self._changes.audit(resource, input_data.actor_id, AuditAction.CREATE, now)
        return self._changes.synced_view(resource)

    def _address_of(self, feed: IcalImportFeed) -> str:
        return str(self._secret_cipher.decrypt(feed.encrypted_url))
