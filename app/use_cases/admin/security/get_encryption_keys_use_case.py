from app.contracts.key_rotations import KeyRotationRepoContract
from app.contracts.secret_cipher import SecretRotationAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.key_rotations import KeyRotationDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.key_rotation import EncryptionKeysQuery, EncryptionKeysView
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.security.key_rotation_views import build_key_rotation_view


class GetEncryptionKeysUseCase(
    UseCaseContract[EncryptionKeysQuery, EncryptionKeysView]
):
    """
    The platform admin's view of the key ring: how many keys it holds (never
    the keys) and how the latest re-encryption run went.

    Raises:
        AccessDeniedError: the user is not a platform admin.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[UserId, UserDocument],
        secret_rotation: SecretRotationAdapterContract,
        key_rotation_repo: KeyRotationRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[UserId, UserDocument] = (
            authorize_platform_admin
        )
        self._secret_rotation: SecretRotationAdapterContract = secret_rotation
        self._key_rotation_repo: KeyRotationRepoContract = key_rotation_repo

    def run(self, input_data: EncryptionKeysQuery) -> EncryptionKeysView:
        self._authorize_platform_admin.run(input_data.user_id)
        latest: KeyRotationDocument | None = self._key_rotation_repo.get_latest()
        return EncryptionKeysView(
            key_count=self._secret_rotation.key_count(),
            latest_rotation=None if latest is None else build_key_rotation_view(latest),
        )
