"""Who is a platform admin: the PLATFORM_ADMIN_* lists, read at every check."""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.users import UserDocument


def is_listed_platform_admin(user: UserDocument, settings: AppSettings) -> bool:
    """
    True when the user's phone or e-mail is on the admin lists of these
    settings. The flag stored on the user (`is_platform_admin`, refreshed at
    sign-in) is never trusted for access: someone taken off the lists loses
    the rights with the next request.
    """

    return (
        user.phone_number is not None
        and user.phone_number in settings.platform_admin_phone_numbers
    ) or (user.email is not None and user.email in settings.platform_admin_emails)
