"""
The ledger of erased customers (data-subject erasures) kept outside the
database, beside the deletion ledger of businesses, so a restore re-applies
them.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId


class ContactErasureRecord(ImmutableDTO):
    """
    One erased customer, as a restore needs it: which business, which
    contact and when their data was erased. Ids only, nothing personal.
    Also the payload of the queued job "record_contact_erasure".
    """

    business_id: BusinessId
    contact_id: ContactId
    erased_at: Microseconds
