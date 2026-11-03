"""
Who sees a booking's health note in the cabinet (PRIV-10): the owner and
the staff who serve customers; an agency helper and platform support see
only that a note is withheld. Notes without health data are shown to all.
"""

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.brand_repositories import BrandRepository
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessMember
from app.schemas.dto.booking_grid import BookingGridQuery
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.bookings import ListBookingsQuery
from app.schemas.typings.bookings.constrained_integers import BookingGridDayCount
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.bookings.calendar.get_booking_grid_use_case import (
    GetBookingGridUseCase,
)
from app.use_cases.bookings.list_bookings_use_case import ListBookingsUseCase
from app.utilities.integrations.public_views import public_booking
from tests.bookings_calendar.grid_world import GridWorld

HEALTH_NOTE: BookingNote = BookingNote("Severe nut allergy")
PLAIN_NOTE: BookingNote = BookingNote("High chair")


class TeamWorld:
    """Two bookings (one with a health note) and every kind of viewer."""

    def __init__(self) -> None:
        self.grid = GridWorld()
        world = self.grid.world
        self.owner_id: UserId = next(
            member.user_id
            for member in self.grid.business.members
            if member.role is BusinessMemberRole.OWNER
        )
        self.agency_id = UserId()
        self.support_id = UserId()
        business = self.grid.business.model_copy(
            update={
                "members": [
                    *self.grid.business.members,
                    BusinessMember(
                        user_id=self.agency_id, role=BusinessMemberRole.AGENCY
                    ),
                ]
            }
        )
        world.business_repo.save(business)
        self.grid.business = business
        for place, note in (
            (self.grid.window, HEALTH_NOTE),
            (self.grid.terrace, PLAIN_NOTE),
        ):
            booking = self.grid.book(place, "2026-10-06T19:00", "2026-10-06T21:00")
            world.booking_repo.save(booking.model_copy(update={"notes": note}))
        self.brands = BrandRepository(
            InMemoryDocumentCollectionAdapter[BrandDocument](BrandDocument)
        )

    def listed(self, viewer: UserId) -> list[BookingView]:
        world = self.grid.world
        return (
            ListBookingsUseCase(
                business_repo=world.business_repo,
                booking_repo=world.booking_repo,
                resource_repo=world.resource_repo,
                knowledge_item_repo=world.knowledge_repo,
                contact_repo=world.contact_repo,
                audit_log_repo=world.audit_repo,
                wall_clock=world.clock.wall_clock,
                brand_repo=self.brands,
            )
            .run(ListBookingsQuery(business_id=self.grid.business.id, actor_id=viewer))
            .items
        )

    def on_the_grid(self, viewer: UserId) -> list[BookingView]:
        world = self.grid.world
        use_case = GetBookingGridUseCase(
            business_repo=world.business_repo,
            business_profile_repo=world.profile_repo,
            resource_repo=world.resource_repo,
            schedule_exception_repo=world.exception_repo,
            booking_repo=world.booking_repo,
            knowledge_item_repo=world.knowledge_repo,
            contact_repo=world.contact_repo,
            audit_log_repo=world.audit_repo,
            wall_clock=world.clock.wall_clock,
            brand_repo=self.brands,
        )
        return use_case.run(
            BookingGridQuery(
                business_id=self.grid.business.id,
                actor_id=viewer,
                date_from=LocalDate("2026-10-06"),
                days=BookingGridDayCount(1),
            )
        ).bookings


def notes_seen(views: list[BookingView]) -> list[tuple[str | None, bool]]:
    return sorted(
        (
            (
                None if view.notes is None else str(view.notes),
                view.is_health_note_withheld,
            )
            for view in views
        ),
        key=str,
    )


def test_the_owner_and_staff_see_the_health_note() -> None:
    team = TeamWorld()

    for viewer in (team.owner_id, team.grid.staff_id):
        for views in (team.listed(viewer), team.on_the_grid(viewer)):
            assert notes_seen(views) == [
                ("High chair", False),
                ("Severe nut allergy", False),
            ]


def test_an_agency_helper_and_platform_support_see_it_withheld() -> None:
    team = TeamWorld()

    for viewer in (team.agency_id, team.support_id):
        for views in (team.listed(viewer), team.on_the_grid(viewer)):
            assert notes_seen(views) == [("High chair", False), (None, True)]


def test_the_public_api_and_webhooks_never_carry_a_health_note() -> None:
    team = TeamWorld()
    grid = team.grid
    stored = sorted(
        grid.world.booking_repo.list_by_business(grid.business.id),
        key=lambda booking: str(booking.notes),
    )

    shown = [
        public_booking(grid.business, booking, None, None, None, None).notes
        for booking in stored
    ]

    assert shown == [PLAIN_NOTE, None]
