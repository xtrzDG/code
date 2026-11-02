import secrets

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.booking_manage import RevokeBookingLinksCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.constrained_integers import BookingLinkGeneration
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

BOOKING_LINKS_ENTITY: AuditEntityName = AuditEntityName("booking_manage_links")
UNKNOWN_BOOKING_MESSAGE: str = "Booking not found."
# 24 bits, the size a manage link carries.
GENERATION_BITS: int = 24


class RevokeBookingLinksUseCase(UseCaseContract[RevokeBookingLinksCommand, None]):
    """
    Staff end every manage link of a booking sent so far (a link forwarded
    or seen by someone else): the booking draws a new random link
    generation, and a link or page credential of another generation no
    longer opens (`ManagedBookingPages.current`, `link_expired`). Links made
    from now on (a new confirmation, the page's own answers) carry the new
    generation. The business was authorized at the route (any member);
    audited as an UPDATE of `booking_manage_links`.
    """

    def __init__(
        self,
        booking_repo: BookingRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._booking_repo: BookingRepoContract = booking_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RevokeBookingLinksCommand) -> None:
        booking: BookingDocument | None = self._booking_repo.get(
            input_data.business_id, input_data.booking_id
        )
        if booking is None or booking.is_sandbox:
            raise NotFoundError(UNKNOWN_BOOKING_MESSAGE)

        def renew(stored: BookingDocument) -> BookingDocument:
            return stored.model_copy(
                update={
                    "manage_link_generation": draw_generation(
                        stored.manage_link_generation
                    )
                }
            )

        if (
            self._booking_repo.update(
                input_data.business_id, input_data.booking_id, renew
            )
            is None
        ):
            raise NotFoundError(UNKNOWN_BOOKING_MESSAGE)

        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=input_data.business_id,
                actor_id=input_data.actor_id,
                action=AuditAction.UPDATE,
                entity=BOOKING_LINKS_ENTITY,
                entity_id=AuditEntityReference(str(input_data.booking_id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )


def draw_generation(current: BookingLinkGeneration) -> BookingLinkGeneration:
    """A random generation other than the current one and other than 0."""

    while True:
        drawn: int = secrets.randbits(GENERATION_BITS)
        if drawn not in {0, int(current)}:
            return BookingLinkGeneration(drawn)
