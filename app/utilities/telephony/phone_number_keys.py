"""Identities of rented numbers: the business's one request."""

from uuid import UUID, uuid5

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.telephony.prefixed_id import PhoneNumberRequestId

# A fixed namespace of derived ids (never change it: stored ids depend on it).
PHONE_NUMBER_REQUEST_NAMESPACE: UUID = UUID("d9f294c1-b420-4594-8e3b-77d7167866a2")


def phone_number_request_id_of(business_id: BusinessId) -> PhoneNumberRequestId:
    """One request document per business."""

    return PhoneNumberRequestId(uuid5(PHONE_NUMBER_REQUEST_NAMESPACE, str(business_id)))
