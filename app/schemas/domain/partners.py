from base_pydantic_schemas import BaseDocument

from app.schemas.constants.referrals import PartnerStatus
from app.schemas.constants.users import LoginMethod
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.referrals.constrained_integers import (
    CommissionRateBasisPoints,
)
from app.schemas.typings.referrals.constrained_strings import PartnerName
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.schemas.typings.users.prefixed_id import UserId


class PartnerDocument(BaseDocument):
    """
    A partner of the platform: an agency or a consultant who brings
    businesses and earns `commission_rate_basis_points` of every invoice
    those businesses pay, before tax (a platform collection, migration
    1150).

    The partner signs in with the phone number or e-mail recorded here, so
    a partner can be added before their first sign-in; the id derives from
    that destination (one partner per person). `added_by` is the platform
    admin who added them. A PAUSED partner earns nothing new.
    """

    id: PartnerId
    name: PartnerName
    login_method: LoginMethod
    phone_number: E164PhoneNumber | None = None
    email: EmailAddress | None = None
    commission_rate_basis_points: CommissionRateBasisPoints
    status: PartnerStatus = PartnerStatus.ACTIVE
    added_by: UserId
