"""The derived id of a business's current website import."""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.website_import.prefixed_id import WebsiteImportRecordId

# Fixed namespace of the derived ids (never change it: stored ids depend on it).
WEBSITE_IMPORT_NAMESPACE: UUID = UUID("5e0b7c42-91d3-4a6f-8b2e-3c9f1d7a4e65")


def derive_website_import_record_id(business_id: BusinessId) -> WebsiteImportRecordId:
    """One current website import per business: the same business, the same id."""

    return WebsiteImportRecordId(uuid5(WEBSITE_IMPORT_NAMESPACE, str(business_id)))
