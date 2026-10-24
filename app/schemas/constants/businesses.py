from enum import IntEnum, StrEnum


class BusinessStatus(StrEnum):
    """Lifecycle of a business (tenant), as in the concept's tenants table."""

    ONBOARDING = "onboarding"
    TESTING = "testing"
    LIVE = "live"
    PAUSED = "paused"


class ServiceMode(StrEnum):
    """
    What the assistant may do for customers.

    LEADS_ONLY is used after an unpaid subscription's grace period: the
    assistant only takes requests and passes them to staff.
    """

    FULL = "full"
    LEADS_ONLY = "leads_only"


class Weekday(IntEnum):
    """ISO weekday number (Monday is 1)."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class BusinessLinkKind(StrEnum):
    """
    Links from the profile the assistant may send (send_link tool). PRIVACY
    is the business's own privacy notice; the website chat links to it (or,
    without one, to the platform's default notice for the business).
    GOOGLE_REVIEW is the business's Google review page, which every
    customer who rates a visit is invited to (Settings → Reviews).
    """

    MENU = "menu"
    MAP = "map"
    PAYMENT = "payment"
    BOOKING_PAGE = "booking_page"
    DELIVERY = "delivery"
    WEBSITE = "website"
    PRIVACY = "privacy"
    GOOGLE_REVIEW = "google_review"


class BusinessSettingsRefusalCode(StrEnum):
    """Machine-readable reasons a settings change is refused (409, 412)."""

    # The change was made from an older revision: someone saved since.
    STALE_REVISION = "stale_revision"
    # The If-Match header names another revision than the stored one (412).
    PRECONDITION_FAILED = "precondition_failed"
