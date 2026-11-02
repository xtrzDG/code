import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.platform_admins import (
    PlatformAdminRegistryContract,
    PlatformAdminRepoContract,
)
from app.contracts.repositories.passkey_repositories import PasskeyRepoContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.users import UserDocument
from app.utilities.security.platform_admin_ids import derive_platform_admin_id
from app.utilities.security.platform_admins import is_listed_platform_admin

logger: logging.Logger = logging.getLogger(__name__)


class PlatformAdminRegistry(PlatformAdminRegistryContract):
    """
    Platform admin roles from the admin team (`platform_admins`), read at
    every call: removing someone or changing their role takes effect with
    their next request.

    The PLATFORM_ADMIN_* lists only bootstrap a new platform: while the
    team has no SUPER admin, a listed person is recorded as SUPER when they
    are first checked (and their record then decides, like anyone's).
    Once a SUPER admin exists the lists grant nothing; the Team page adds
    and removes admins. Should the last SUPER record ever disappear, the
    lists work again (the way back in).

    Where ADMIN_PASSKEY_REQUIRED is on (production), an admin without a
    passkey is told to add one before the admin pages open; without the
    passkey store every admin is (fail closed).
    """

    def __init__(
        self,
        platform_admin_repo: PlatformAdminRepoContract,
        app_settings: AppSettings,
        wall_clock: WallClock[Microseconds],
        passkey_repo: PasskeyRepoContract | None = None,
    ) -> None:
        self._passkey_repo: PasskeyRepoContract | None = passkey_repo
        self._platform_admin_repo: PlatformAdminRepoContract = platform_admin_repo
        self._app_settings: AppSettings = app_settings
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def role_of(self, user: UserDocument) -> PlatformAdminRole | None:
        record: PlatformAdminDocument | None = self._record_of(user)
        if record is not None:
            return record.role

        if not is_listed_platform_admin(user, self._app_settings):
            return None

        if self._platform_admin_repo.list_by_role(PlatformAdminRole.SUPER):
            return None

        record = self._bootstrap(user)
        return None if record is None else record.role

    def needs_passkey(self, user: UserDocument) -> bool:
        if not self._app_settings.sessions.is_admin_passkey_required:
            return False

        return (
            self._passkey_repo is None
            or int(self._passkey_repo.count_for_user(user.id)) == 0
        )

    def _record_of(self, user: UserDocument) -> PlatformAdminDocument | None:
        if user.login_method is LoginMethod.PHONE and user.phone_number is not None:
            return self._platform_admin_repo.find_by_phone_number(user.phone_number)

        if user.email is not None:
            return self._platform_admin_repo.find_by_email(user.email)

        return None

    def _bootstrap(self, user: UserDocument) -> PlatformAdminDocument | None:
        now: Microseconds = self._wall_clock.now_unix()
        is_phone: bool = user.login_method is LoginMethod.PHONE
        if is_phone and user.phone_number is not None:
            admin_id = derive_platform_admin_id(LoginMethod.PHONE, user.phone_number)
        elif not is_phone and user.email is not None:
            admin_id = derive_platform_admin_id(LoginMethod.EMAIL, user.email)
        else:
            return None

        record = PlatformAdminDocument(
            id=admin_id,
            login_method=user.login_method,
            phone_number=user.phone_number if is_phone else None,
            email=None if is_phone else user.email,
            role=PlatformAdminRole.SUPER,
            created_at=now,
            updated_at=now,
        )
        self._platform_admin_repo.save(record)
        logger.warning(
            "Platform admin %s bootstrapped as SUPER from the PLATFORM_ADMIN_* lists.",
            user.id,
        )
        return record
