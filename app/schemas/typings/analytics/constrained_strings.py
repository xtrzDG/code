"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString

# Printable text without control characters or angle brackets: campaign
# names come from links anyone can write.
CAMPAIGN_TEXT_PATTERN: str = r"^[^\x00-\x1f\x7f<>]+$"


class AcquisitionSourceKey(BaseConstrainedTypedString):
    """
    Where an owner came from, normalized for the founder's reports: the
    campaign source, the `src` tag, `referral`, `hosted_chat`, the
    referring site, `direct` or `unknown` (lower case).

    Example:
        source = AcquisitionSourceKey("instagram")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[a-z0-9][a-z0-9._:-]*$"


class CabinetRoutePattern(BaseConstrainedTypedString):
    """
    A cabinet page as its route template, never with ids or query values,
    so a measurement names no business or customer.

    Example:
        route = CabinetRoutePattern("/b/[businessId]/inbox")
    """

    min_length = 1
    max_length = 160
    pattern = r"^/[A-Za-z0-9_\-\[\]/.]*$"


class CohortMonth(BaseConstrainedTypedString):
    """
    The calendar month (UTC) of a sign-up cohort, as YYYY-MM.

    Example:
        month = CohortMonth("2026-09")
    """

    min_length = 7
    max_length = 7
    pattern = r"^\d{4}-(0[1-9]|1[0-2])$"


class LandingPath(BaseConstrainedTypedString):
    """
    The page of this site a visitor first opened (path only, no query).

    Example:
        path = LandingPath("/c/cafe-tbilisi")
    """

    min_length = 1
    max_length = 200
    pattern = r"^/[A-Za-z0-9_\-/.~%]*$"


class MetricsDate(BaseConstrainedTypedString):
    """
    A calendar day (UTC) bounding the founder's metrics, as YYYY-MM-DD.

    Example:
        start = MetricsDate("2026-09-01")
    """

    min_length = 10
    max_length = 10
    pattern = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"


class ReferralCode(BaseConstrainedTypedString):
    """
    The `ref` code of the link a visitor came by (a partner or a referring
    owner).

    Example:
        code = ReferralCode("partner-42")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9._-]+$"


class ReferrerHost(BaseConstrainedTypedString):
    """
    The site a visitor came from (host name only, lower case).

    Example:
        host = ReferrerHost("www.google.com")
    """

    min_length = 1
    max_length = 253
    pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$"


class SignupSourceTag(BaseConstrainedTypedString):
    """
    The `src` tag of the link a visitor came by (a QR card, a widget's
    "Powered by" link).

    Example:
        tag = SignupSourceTag("qr")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9._-]+$"


class UtmCampaign(BaseConstrainedTypedString):
    """The `utm_campaign` of the link a visitor came by."""

    min_length = 1
    max_length = 120
    pattern = CAMPAIGN_TEXT_PATTERN


class UtmContent(BaseConstrainedTypedString):
    """The `utm_content` of the link a visitor came by."""

    min_length = 1
    max_length = 120
    pattern = CAMPAIGN_TEXT_PATTERN


class UtmMedium(BaseConstrainedTypedString):
    """The `utm_medium` of the link a visitor came by (cpc, email, social)."""

    min_length = 1
    max_length = 120
    pattern = CAMPAIGN_TEXT_PATTERN


class UtmSource(BaseConstrainedTypedString):
    """The `utm_source` of the link a visitor came by (google, instagram)."""

    min_length = 1
    max_length = 120
    pattern = CAMPAIGN_TEXT_PATTERN


class UtmTerm(BaseConstrainedTypedString):
    """The `utm_term` of the link a visitor came by."""

    min_length = 1
    max_length = 120
    pattern = CAMPAIGN_TEXT_PATTERN


# Keep abc order for all non example types, if possible.
