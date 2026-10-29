"""
The restaurant of the growth world with its tables' calendar settings, a
fake Cal.com behind the real connector, the queue of booking writes and the
job that writes them.
"""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.facilitators.calendar_sync.booking_system_write_queue import (
    BookingSystemWriteQueue,
)
from app.registries.booking_systems.booking_system_connector_registry import (
    BookingSystemConnectorRegistry,
)
from app.repositories.calendar_sync_repositories import (
    ResourceCalendarLinkRepository,
)
from app.schemas.constants.calendar_sync import BookingSystemKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.calendar_sync import (
    BookingSystemLink,
    ResourceCalendarLinkDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.calendar_sync.constrained_strings import (
    BookingSystemResourceId,
)
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.use_cases.calendar_sync.write_booking_system_booking_use_case import (
    WriteBookingSystemBookingUseCase,
)
from app.utilities.calendar_sync.booking_system_jobs import (
    encode_booking_system_write,
)
from app.utilities.calendar_sync.calendar_sync_keys import (
    resource_calendar_link_id_of,
)
from tests.calendar_sync.fake_cal_com import GOOD_KEY, FakeCalCom
from tests.channels.channels_fakes import FakeSecretCipher
from tests.waitlist.growth_world import GrowthWorld

EVENT_TYPE: str = "1203845"
DAY: str = "2026-10-07"


def at(time: str) -> str:
    return f"{DAY}T{time}:00+04:00"


class BookingWriteWorld(GrowthWorld):
    def __init__(self) -> None:
        super().__init__()
        self.cal_com = FakeCalCom()
        self.cipher = FakeSecretCipher()
        self.link_repo = ResourceCalendarLinkRepository(
            InMemoryDocumentCollectionAdapter(ResourceCalendarLinkDocument)
        )
        self.queue = BookingSystemWriteQueue(self.link_repo, self.job_queue)
        self.writer = WriteBookingSystemBookingUseCase(
            booking_repo=self.booking_repo,
            link_repo=self.link_repo,
            contact_repo=self.contact_repo,
            business_repo=self.business_repo,
            connectors=BookingSystemConnectorRegistry([self.cal_com.adapter()]),
            secret_cipher=self.cipher,
            text_resolver=self.resolver,
            wall_clock=self.clock.wall_clock,
        )

    def follow(self, resource: ResourceDocument, key: str = GOOD_KEY) -> None:
        """The table follows the Cal.com event type with the business's key."""

        now: Microseconds = self.clock.now_microseconds()
        self.link_repo.add(
            ResourceCalendarLinkDocument(
                id=resource_calendar_link_id_of(resource.id),
                business_id=resource.business_id,
                resource_id=resource.id,
                booking_system=BookingSystemLink(
                    kind=BookingSystemKind.CAL_COM,
                    external_resource_id=BookingSystemResourceId(EVENT_TYPE),
                    encrypted_api_key=self.cipher.encrypt(ChannelSecret(key)),
                    added_at=now,
                ),
                created_at=now,
                updated_at=now,
            )
        )

    def unfollow(self, resource: ResourceDocument) -> None:
        self.link_repo.update(
            resource.business_id,
            resource.id,
            lambda current: current.model_copy(update={"booking_system": None}),
        )

    def evening(
        self, resource: ResourceDocument | None = None, name: str = "Nino"
    ) -> BookingDocument:
        """A booking from 19:00 to 21:00 (15:00 to 17:00 UTC)."""

        return self.add_booking(
            self.business,
            resource or self.table_for_four,
            self.guest(name, "ru"),
            at("19:00"),
            at("21:00"),
        )

    def write(self, booking: BookingDocument, is_final: bool = False) -> JobReport:
        return self.writer.run(
            QueuedJobInput(
                job_id=QueuedJobId(),
                job_name=JobName("write_booking_system_booking"),
                payload=encode_booking_system_write(booking.business_id, booking.id),
                business_id=booking.business_id,
                is_final_attempt=is_final,
            )
        )

    def stored(self, booking: BookingDocument) -> BookingDocument:
        found = self.booking_repo.get(booking.business_id, booking.id)
        assert found is not None
        return found

    def changed(self, booking: BookingDocument, **fields: object) -> BookingDocument:
        """The booking as staff changed it (status, times, table)."""

        updated = self.stored(booking).model_copy(update=fields)
        self.booking_repo.save(updated)
        return updated

    def link_of(self, resource: ResourceDocument) -> BookingSystemLink:
        link = self.link_repo.get(resource.business_id, resource.id)
        assert link is not None and link.booking_system is not None
        return link.booking_system
