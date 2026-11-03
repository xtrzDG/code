"""
The cabinet's answers to a booking change (PRIV-10): a booking whose notes
hold health data comes back with them only to the owner and the staff who
serve customers (`health_note_privacy`), as the bookings list, the
calendar grid and the conversation card show it. Without this an agency
helper would read the note it may not see from the answer to any change
it may make (a PATCH that changes nothing, an Undo, a cancellation).
"""

from typing import Protocol

from app.contracts.repositories.brand_repositories import BrandRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.bookings import BookingResult, BookingView
from app.schemas.typings.bookings.booleans import SeesHealthNotes
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.health_note_privacy import (
    protect_health_note,
    sees_health_notes,
)


class BookingChangeCommand(Protocol):
    """A booking change made in the cabinet: the business and who made it."""

    @property
    def business_id(self) -> BusinessId: ...

    @property
    def actor_id(self) -> UserId | None: ...


class HealthNoteGuardedUseCase[
    Command: BookingChangeCommand,
    Answer: (BookingView, BookingResult),
](UseCaseContract[Command, Answer]):
    """
    `use_case`'s answer as the person who made the change may see it: a
    health note withheld (`is_health_note_withheld`) from anyone but the
    owner and staff. A change without a person (the assistant's tools, a
    customer's own booking link) and notes without health data come back
    as they are.
    """

    def __init__(
        self,
        use_case: UseCaseContract[Command, Answer],
        business_repo: BusinessRepoContract,
        brand_repo: BrandRepoContract | None = None,
    ) -> None:
        self._use_case: UseCaseContract[Command, Answer] = use_case
        self._business_repo: BusinessRepoContract = business_repo
        self._brand_repo: BrandRepoContract | None = brand_repo

    def run(self, input_data: Command) -> Answer:
        answer: Answer = self._use_case.run(input_data)
        actor_id: UserId | None = input_data.actor_id
        if actor_id is None:
            return answer

        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            return answer

        sees_notes: SeesHealthNotes = sees_health_notes(
            self._brand_repo, business, actor_id
        )
        if isinstance(answer, BookingResult):
            return answer.model_copy(
                update={"booking": protect_health_note(answer.booking, sees_notes)}
            )

        return protect_health_note(answer, sees_notes)
