"""
Upcasters of the stored subscriptions (`document_upgrades` registers them).

Version 5 names who runs a subscription's automatic charges
(`payment_provider`). Before it Flitt was the only provider, so a version
4 row with charges running (`provider_reference`) is Flitt's; one
without stays without.
"""

from app.schemas.constants.payments import PaymentProvider

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]

PROVIDER_REFERENCE_FIELD_NAME: str = "provider_reference"
PAYMENT_PROVIDER_FIELD_NAME: str = "payment_provider"


def upgrade_subscriptions_from_v4(document: StoredJsonObject) -> StoredJsonObject:
    """A row with automatic charges running gets Flitt as their provider."""

    if (
        document.get(PROVIDER_REFERENCE_FIELD_NAME) is None
        or document.get(PAYMENT_PROVIDER_FIELD_NAME) is not None
    ):
        return document

    upgraded: StoredJsonObject = dict(document)
    upgraded[PAYMENT_PROVIDER_FIELD_NAME] = PaymentProvider.FLITT.value
    return upgraded
