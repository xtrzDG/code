from base_pydantic_schemas import BaseDocument

from app.schemas.constants.access import PlatformAdminRole
from app.schemas.constants.users import LoginMethod
from app.schemas.typings.access.prefixed_id import PlatformAdminId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId


class PlatformAdminDocument(BaseDocument):
    """
    A person allowed into the platform admin pages, and what for (a
    platform collection, migration 1103).

    The person is named by the phone number or e-mail they sign in with,
    so a record can exist before their first sign-in; the id derives from
    that destination (one record per person). `added_by` is the SUPER
    admin who added them (None: bootstrapped from the PLATFORM_ADMIN_*
    lists while no SUPER admin was recorded). Rights are read from these
    records at every request: a removed record or a changed role takes
    effect at once.
    """

    id: PlatformAdminId
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    role: PlatformAdminRole
    added_by: UserId | None = None

