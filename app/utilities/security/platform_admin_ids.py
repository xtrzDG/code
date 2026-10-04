"""The id of a platform admin's record, derived from how they sign in."""

from uuid import UUID, uuid5

from app.schemas.constants.users import LoginMethod
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress

PLATFORM_ADMIN_NAMESPACE: UUID = UUID("5d3f0d4e-9b1c-4c55-8a3e-1f0e6b7a2c91")


def derive_platform_admin_id(
    login_method: LoginMethod, destination: E164PhoneNumber | EmailAddress
) -> PlatformAdminId:
    """The same person (phone or e-mail): the same record, added once."""

    return PlatformAdminId(
        uuid5(PLATFORM_ADMIN_NAMESPACE, f"{login_method.value}|{destination}")
    )
