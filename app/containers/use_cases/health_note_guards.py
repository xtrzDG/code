from dependency_injector.providers import Factory, Provider

from app.containers.repositories import RepositoriesContainer
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.bookings import BookingResult, BookingView
from app.use_cases.bookings.health_note_guard import (
    BookingChangeCommand,
    HealthNoteGuardedUseCase,
)


def health_note_guarded[
    Command: BookingChangeCommand,
    Answer: (BookingView, BookingResult),
](
    use_case: Provider[UseCaseContract[Command, Answer]],
    repositories: RepositoriesContainer,
) -> Factory[UseCaseContract[Command, Answer]]:
    """
    A booking change whose answer shows a health note only to the owner and
    staff of the person who made it (PRIV-10, `HealthNoteGuardedUseCase`).
    """

    return Factory(
        HealthNoteGuardedUseCase[Command, Answer],
        use_case=use_case,
        business_repo=repositories.business_repo,
        brand_repo=repositories.brand_repo,
    )
