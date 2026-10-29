"""Customers → settings: whether staff see phone numbers; the business's tags."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.contacts.booleans import StaffSeesCustomerPhones
from app.schemas.typings.contacts.constrained_strings import CustomerTag
from app.schemas.typings.users.prefixed_id import UserId


class CustomerSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class CustomerSettingsRequest(ImmutableDTO):
    staff_sees_phone_numbers: StaffSeesCustomerPhones


class UpdateCustomerSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: CustomerSettingsRequest
    client_ip_address: ClientIpAddress | None = None


class CustomerSettingsView(ImmutableDTO):
    """Off by default: staff see phones masked in Customers and the search."""

    staff_sees_phone_numbers: StaffSeesCustomerPhones = False
    known_tags: list[CustomerTag] = Field(default_factory=list[CustomerTag])
