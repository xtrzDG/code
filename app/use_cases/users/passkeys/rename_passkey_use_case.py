from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.dto.passkeys import PasskeyView, RenamePasskeyCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.users.passkeys.passkey_records import passkey_view

NOT_FOUND_MESSAGE: str = "This passkey was not found."


class RenamePasskeyUseCase(UseCaseContract[RenamePasskeyCommand, PasskeyView]):
    """A person renames one of their passkeys (another person's is not found)."""

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RenamePasskeyCommand) -> PasskeyView:
        passkey: PasskeyDocument | None = self._passkey_repo.get(input_data.passkey_id)
        if passkey is None or passkey.user_id != input_data.user_id:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        renamed: PasskeyDocument | None = self._passkey_repo.rename(
            passkey.id, input_data.name, self._wall_clock.now_unix()
        )
        if renamed is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return passkey_view(renamed)
