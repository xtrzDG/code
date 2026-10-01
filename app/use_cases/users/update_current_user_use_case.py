from typed_time_provider import Microseconds, WallClock

from app.contracts.registries import LanguageRegistryContract
from app.contracts.repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.users import UserDocument
from app.schemas.dto.users import UpdateCurrentUserCommand, UserView
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)

MAX_DISPLAY_NAME_LENGTH: int = 100


class UpdateCurrentUserUseCase(UseCaseContract[UpdateCurrentUserCommand, UserView]):
    """
    Change the signed-in user's display name or interface language.

    Missing fields stay unchanged; a blank display name clears it. The
    language must be known to the language registry (any BCP 47 tag it
    supports, including right-to-left scripts).
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        language_registry: LanguageRegistryContract,
        user_view_transformer: TransformerContract[UserDocument, UserView],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._language_registry: LanguageRegistryContract = language_registry
        self._user_view_transformer: TransformerContract[UserDocument, UserView] = (
            user_view_transformer
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateCurrentUserCommand) -> UserView:
        user: UserDocument | None = self._user_repo.get(input_data.user_id)
        if user is None:
            raise NotFoundError(f"User {input_data.user_id} was not found.")

        if input_data.display_name is not None:
            if len(input_data.display_name) > MAX_DISPLAY_NAME_LENGTH:
                raise ValidationFailedError(
                    "Display name must be at most "
                    f"{MAX_DISPLAY_NAME_LENGTH} characters."
                )

            is_blank: bool = input_data.display_name.strip() == ""
            user.display_name = None if is_blank else input_data.display_name

        if input_data.locale is not None:
            self._language_registry.get(input_data.locale)
            user.locale = input_data.locale

        user.updated_at = self._wall_clock.now_unix()
        self._user_repo.save(user)
        return self._user_view_transformer.transform(user)
