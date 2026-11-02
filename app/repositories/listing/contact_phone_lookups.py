"""
The phone lookups of `ContactRepository`: one contact by a given or a
proved phone, and every contact holding a number. Several contacts may
hold one number (a caller id joins no contact a channel proved), so a
check that refuses a number, such as a blocked caller, reads them all.
"""

from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    PHONE_NUMBER_FIELD,
    VERIFIED_PHONE_NUMBER_FIELD,
)
from app.repositories.document_queries import field_equals
from app.schemas.domain.contacts import ContactDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber


class ContactPhoneLookups(BusinessScopedRepository[ContactDocument]):
    """Indexed reads of contacts by `phone_number` and `verified_phone_number`."""

    def find_by_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        return self._find_in_business(
            business_id, [field_equals(PHONE_NUMBER_FIELD, phone_number)]
        )

    def find_by_verified_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> ContactDocument | None:
        return self._find_in_business(
            business_id, [field_equals(VERIFIED_PHONE_NUMBER_FIELD, phone_number)]
        )

    def list_by_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> list[ContactDocument]:
        return self._list_in_business(
            business_id, [field_equals(PHONE_NUMBER_FIELD, phone_number)]
        )

    def list_by_verified_phone_number(
        self,
        business_id: BusinessId,
        phone_number: E164PhoneNumber,
    ) -> list[ContactDocument]:
        return self._list_in_business(
            business_id, [field_equals(VERIFIED_PHONE_NUMBER_FIELD, phone_number)]
        )
