"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class MetaTokenRefreshDays(BaseConstrainedTypedInt):
    """
    How many days before a WhatsApp Embedded Signup token ends the platform
    asks Meta to renew it (META_TOKEN_REFRESH_DAYS), 1..60: Meta issues the
    business's token for 60 days, so 60 renews a token at the first run
    after it was issued.

    Example:
        refresh_days = MetaTokenRefreshDays(15)
    """

    ge = 1
    le = 60


# Keep abc order for all non example types, if possible.
