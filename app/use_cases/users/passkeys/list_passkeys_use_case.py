from app.contracts.passkeys import PasskeyCeremonyAdapterContract
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.passkeys import PasskeyDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.passkeys import PasskeyListView
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.users.passkeys.passkey_records import passkey_view


class ListPasskeysUseCase(UseCaseContract[UserId, PasskeyListView]):
    """
    The signed-in person's passkeys (Account → Security), newest first,
    whether this server offers passkeys, and whether one is recommended:
    a platform admin without a usable one should add one (phishing-
    resistant sign-in to the admin pages).
    """

    def __init__(
        self,
        passkey_repo: PasskeyRepoContract,
        user_repo: UserRepoContract,
        ceremony: PasskeyCeremonyAdapterContract,
    ) -> None:
        self._passkey_repo: PasskeyRepoContract = passkey_repo
        self._user_repo: UserRepoContract = user_repo
        self._ceremony: PasskeyCeremonyAdapterContract = ceremony

    def run(self, input_data: UserId) -> PasskeyListView:
        passkeys: list[PasskeyDocument] = self._passkey_repo.list_for_user(input_data)
        user: UserDocument | None = self._user_repo.get(input_data)
        is_available: bool = self._ceremony.is_available()
        return PasskeyListView(
            items=[passkey_view(passkey) for passkey in passkeys],
            is_available=is_available,
            is_recommended=is_available
            and user is not None
            and user.is_platform_admin
            and not any(passkey.clone_suspected_at is None for passkey in passkeys),
        )
