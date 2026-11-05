"""
Changes of a booking whose notes hold health data (PRIV-10): the answer to
a change carries the note only to the owner and staff, as the bookings list
does, so an agency helper cannot read it back from a change that changes
nothing, an Undo or a cancellation; and only those who see the note may
replace it (an allergy note overwritten unseen would no longer reach the
staff).
"""

import pytest

from app.containers.app import AppContainer
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessMember
from app.schemas.dto.bookings import BookingResult, BookingView, CancelBookingCommand
from app.schemas.dto.operations.bookings import UpdateBookingCommand
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.schemas.typings.bookings.strings import BookingNote
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.bookings.health_note_guard import HealthNoteGuardedUseCase
from tests.operations.cabinet_bookings_helpers import Cabinet

HEALTH_NOTE: BookingNote = BookingNote("Severe nut allergy")


class AgencyCabinet:
    """A business with an agency helper and a booking with a health note."""

    def __init__(self) -> None:
        self.cabinet = Cabinet()
        world = self.cabinet.world
        self.agency_id = UserId()
        self.owner_id: UserId = next(
            member.user_id
            for member in self.cabinet.business.members
            if member.role is BusinessMemberRole.OWNER
        )
        business = self.cabinet.business.model_copy(
            update={
                "members": [
                    *self.cabinet.business.members,
                    BusinessMember(
                        user_id=self.agency_id, role=BusinessMemberRole.AGENCY
                    ),
                ]
            }
        )
        world.business_repo.save(business)
        self.cabinet.business = business
        booking = world.add_booking(
            business,
            self.cabinet.table,
            self.cabinet.customer,
            "2026-10-06T19:00:00+04:00",
            "2026-10-06T21:00:00+04:00",
        )
        self.booking: BookingDocument = booking.model_copy(
            update={"notes": HEALTH_NOTE}
        )
        world.booking_repo.save(self.booking)

    def command(
        self, actor_id: UserId, notes: BookingNote | None = None
    ) -> UpdateBookingCommand:
        """A change of nothing but, maybe, the notes."""

        return UpdateBookingCommand(
            business_id=self.cabinet.business.id,
            actor_id=actor_id,
            booking_id=self.booking.id,
            party_size=self.booking.party_size,
            notes=notes,
        )

    def guarded_update(
        self,
    ) -> HealthNoteGuardedUseCase[UpdateBookingCommand, BookingView]:
        return HealthNoteGuardedUseCase(
            self.cabinet.world.update_booking(), self.cabinet.world.business_repo
        )

    def stored_notes(self) -> BookingNote | None:
        stored = self.cabinet.world.booking_repo.get(
            self.cabinet.business.id, self.booking.id
        )
        assert stored is not None
        return stored.notes


class FixedAnswer:
    """A booking change that answers with the given result."""

    def __init__(self, result: BookingResult) -> None:
        self.result: BookingResult = result

    def run(self, input_data: CancelBookingCommand) -> BookingResult:
        return self.result


def test_the_answer_to_a_change_withholds_the_note_from_an_agency_helper() -> None:
    team = AgencyCabinet()

    answer = team.guarded_update().run(team.command(team.agency_id))

    assert (answer.notes, answer.is_health_note_withheld) == (None, True)
    for viewer in (team.owner_id, team.cabinet.staff_id):
        shown = team.guarded_update().run(team.command(viewer))
        assert (shown.notes, shown.is_health_note_withheld) == (HEALTH_NOTE, False)


def test_a_cancellations_answer_withholds_it_and_a_customers_keeps_it() -> None:
    team = AgencyCabinet()
    view = team.cabinet.world.update_booking().run(team.command(team.owner_id))
    result = BookingResult(booking=view, confirmation_text=MessageText("Cancelled."))
    guarded = HealthNoteGuardedUseCase[CancelBookingCommand, BookingResult](
        FixedAnswer(result), team.cabinet.world.business_repo
    )

    def cancelled_by(actor_id: UserId | None) -> BookingView:
        return guarded.run(
            CancelBookingCommand(
                business_id=team.cabinet.business.id,
                booking_id=team.booking.id,
                language=LanguageTag("en"),
                actor_id=actor_id,
            )
        ).booking

    by_agency = cancelled_by(team.agency_id)
    assert (by_agency.notes, by_agency.is_health_note_withheld) == (None, True)
    # The assistant's tools and a customer's own booking link name no one.
    assert cancelled_by(None).notes == HEALTH_NOTE
    assert cancelled_by(team.cabinet.staff_id).notes == HEALTH_NOTE


def test_an_agency_helper_may_not_replace_a_note_it_cannot_see() -> None:
    team = AgencyCabinet()

    for notes in ("VIP guest", ""):
        with pytest.raises(AccessDeniedError):
            team.cabinet.world.update_booking().run(
                team.command(team.agency_id, BookingNote(notes))
            )

    assert team.stored_notes() == HEALTH_NOTE


def test_the_owner_and_staff_change_it_and_a_helper_changes_the_rest() -> None:
    team = AgencyCabinet()
    update = team.cabinet.world.update_booking()

    update.run(team.command(team.cabinet.staff_id, BookingNote("Nut allergy, table 4")))
    assert team.stored_notes() == "Nut allergy, table 4"

    moved = update.run(
        UpdateBookingCommand(
            business_id=team.cabinet.business.id,
            actor_id=team.agency_id,
            booking_id=team.booking.id,
            party_size=PartySize(3),
            status=BookingStatus.CONFIRMED,
        )
    )
    assert int(moved.party_size) == 3
    assert team.stored_notes() == "Nut allergy, table 4"


def test_the_cabinets_booking_changes_answer_through_the_guard() -> None:
    bookings = AppContainer().use_cases.bookings

    for change in (
        bookings.update_booking_use_case(),
        bookings.revert_booking_status_use_case(),
        bookings.cancel_booking_use_case(),
        bookings.reschedule_booking_use_case(),
    ):
        assert isinstance(change, HealthNoteGuardedUseCase)
