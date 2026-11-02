from enum import StrEnum


class LoginMethod(StrEnum):
    """Identifier a user signs in with."""

    PHONE = "phone"
    EMAIL = "email"


class BusinessMemberRole(StrEnum):
    """
    Role of a user inside one business. AGENCY is an outside helper (a
    partner's agency) the owner let in: staff's work plus building and
    publishing the assistant, never billing, the team, channels, security
    or copies of customers' data.
    """

    OWNER = "owner"
    STAFF = "staff"
    AGENCY = "agency"


class LoginRiskSignal(StrEnum):
    """
    Why a login code request needs a bot check (Cloudflare Turnstile)
    before the paid send. None depends on whether the phone or e-mail
    belongs to someone, so the answer never tells (no enumeration): every
    phone is checked (SMS_DESTINATION, a paid text message that SMS
    pumping abuses), and the rest look at the client and the platform.
    Answers only (never stored).
    """

    SMS_DESTINATION = "sms_destination"
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
    were replaced, their platform-admin role was given, changed or taken
    away, they signed out everywhere, a platform admin ended them, or they
    were made an owner of a business (owner rights come with a new
    sign-in). Written only into audit references, never as a stored enum.
    """

    AUTHENTICATOR_REMOVED = "authenticator_removed"
    AUTHENTICATOR_ADDED = "authenticator_added"
    RECOVERY_CODES_REPLACED = "recovery_codes_replaced"
    ADMIN_ROLE_CHANGED = "admin_role_changed"
    ADMIN_ROLE_GRANTED = "admin_role_granted"
    SIGNED_OUT_EVERYWHERE = "signed_out_everywhere"
    ENDED_BY_PLATFORM_ADMIN = "ended_by_platform_admin"
    BUSINESS_ROLE_RAISED = "business_role_raised"
