"""Derived ids of Customers: one customer settings document per business."""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import CustomerSettingsId

# Fixed namespace of the derived id (never change it: stored ids depend on it).
CUSTOMER_SETTINGS_NAMESPACE: UUID = UUID("8f0d3b62-41c7-4e5a-9b18-c6a27e4f9d05")


def derive_customer_settings_id(business_id: BusinessId) -> CustomerSettingsId:
    return CustomerSettingsId(uuid5(CUSTOMER_SETTINGS_NAMESPACE, str(business_id)))
