"""Keep abc order."""

from typing import ClassVar, Literal

from base_typed_id import BasePrefixedTypedId


class CommissionEntryId(BasePrefixedTypedId):
    """
    Identifier of a partner's commission on one paid invoice. Derived (UUID
    v5) from the invoice, so an invoice earns its commission once however
    often its payment is reported.
    """

    prefix = "commission_entry"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class PartnerId(BasePrefixedTypedId):
    """
    Identifier of a partner (an agency or a consultant who brings
    businesses). Derived (UUID v5) from the partner's sign-in phone number
    or e-mail, so a person is one partner.
    """

    prefix = "partner"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class ReferralCodeId(BasePrefixedTypedId):
    """
    Identifier of a referral code, derived (UUID v5) from the code in lower
    case: one code names one partner or one business, whatever its case.
    """

    prefix = "referral_code"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


class ReferralId(BasePrefixedTypedId):
    """
    Identifier of the referral of a business that signed up by a code,
    derived (UUID v5) from that business: a business is referred once.
    """

    prefix = "referral"
    uuid_version: ClassVar[Literal[1, 3, 4, 5, 6, 7, 8] | None] = None


# Keep abc order for all non example types, if possible.
