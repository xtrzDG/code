"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class DepositRequestId(BasePrefixedTypedId):
    """
    Identifier of one deposit asked for a booking or a banquet request.

    Example:
        request_id = DepositRequestId()
    """

    prefix = "deposit_request"


class DepositSettingsId(BasePrefixedTypedId):
    """
    Identifier of the deposit settings of one business.

    Derived (UUID v5) from the business, so a business has one document.
    """

    prefix = "deposit_settings"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = 5


class PaymentLinkId(BasePrefixedTypedId):
    """Identifier of one payment page of a business's deposit settings."""

    prefix = "payment_link"


# Keep abc order for all non example types, if possible.
