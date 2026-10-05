from enum import StrEnum


class LoginMethod(StrEnum):
    """Identifier a user signs in with."""

    PHONE = "phone"
    EMAIL = "email"


class BusinessMemberRole(StrEnum):
    """Role of a user inside one business."""

    OWNER = "owner"
    STAFF = "staff"


class LoginRiskSignal(StrEnum):
    """
    Why a login code request needs a bot check (Cloudflare Turnstile)
    before the paid send.
    """

    NEW_DESTINATION = "new_destination"
    BUSY_CLIENT_ADDRESS = "busy_client_address"
    HIGH_PLATFORM_USAGE = "high_platform_usage"
    HIGH_RISK_COUNTRY = "high_risk_country"


class LoginCodeCap(StrEnum):
    """
    A platform-level cap of login code sends per hour; the platform team is
    alerted when one refuses sends (SMS pumping or a login flood).
    """

    COUNTRY = "country"
    NEW_DESTINATIONS = "new_destinations"
    VERIFIED_USERS = "verified_users"


class SessionDeviceKind(StrEnum):
    """
    The kind of device a session's User-Agent describes, for the icon of
    the sessions list; UNKNOWN when it does not say (or there is none).
    """

    DESKTOP = "desktop"
    PHONE = "phone"
    TABLET = "tablet"
    UNKNOWN = "unknown"


class SessionSweepReason(StrEnum):
    """
    Why every session of a person was lowered to one factor or ended: their
    authenticator was removed or a new one confirmed, their recovery codes
    were replaced, or their platform-admin role changed or was taken away.
    """

    AUTHENTICATOR_REMOVED = "authenticator_removed"
    AUTHENTICATOR_ADDED = "authenticator_added"
    RECOVERY_CODES_REPLACED = "recovery_codes_replaced"
    ADMIN_ROLE_CHANGED = "admin_role_changed"
