from base_pydantic_schemas import BaseDocument
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.booleans import StaffSeesCustomerPhones
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.contacts.prefixed_id import CustomerSettingsId


class CustomerSettingsDocument(BaseDocument):
    """
    How the team of one business works with its customers (one document
    per business, the id derived from it; the defaults hold without one).

    `staff_sees_phone_numbers`: off by default, staff see customers' phones
    in Customers and the search masked ("+995 ••• ••• •34"); the owner may
    allow them. `known_tags`: the tags the team used, the latest first (at
    most 100), offered when tagging and when building a segment.
    """

    id: CustomerSettingsId
    business_id: BusinessId
    staff_sees_phone_numbers: StaffSeesCustomerPhones = False
    known_tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])
