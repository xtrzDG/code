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
