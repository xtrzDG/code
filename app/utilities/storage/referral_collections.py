"""
The catalog entries of the referral and partner program (1150), all
platform collections: the partners (by sign-in phone or e-mail, and by
status for the admin's list), the referral codes (keyed by the code; a
partner's codes by partner), the referred businesses (a partner's newest
first; an owner's invitations through the business column) and the
partners' commissions (a partner's newest first, a payout month by
partner, summed per currency and status). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py) and DOCUMENT_LOOKUP_FIELDS
(document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import (
    CommissionEntryDocument,
    ReferralCodeDocument,
    ReferralDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import (
    filter_field,
    integer_field,
    text_field,
)

PARTNERS: DocumentCollectionName = DocumentCollectionName("partners")
REFERRAL_CODES: DocumentCollectionName = DocumentCollectionName("referral_codes")
REFERRALS: DocumentCollectionName = DocumentCollectionName("referrals")
COMMISSION_ENTRIES: DocumentCollectionName = DocumentCollectionName(
    "commission_entries"
)

REFERRAL_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(PARTNERS, PartnerDocument),
    DocumentCollectionDefinition(REFERRAL_CODES, ReferralCodeDocument),
    DocumentCollectionDefinition(REFERRALS, ReferralDocument),
    DocumentCollectionDefinition(COMMISSION_ENTRIES, CommissionEntryDocument),
)

REFERRAL_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    PARTNERS: (
        text_field("phone_number"),
        text_field("email"),
        text_field("status"),
    ),
    REFERRAL_CODES: (text_field("partner_id"),),
    REFERRALS: (
        text_field("partner_id"),
        integer_field("referred_at"),
        integer_field("first_paid_at"),
    ),
    COMMISSION_ENTRIES: (
        text_field("partner_id"),
        text_field("month"),
        filter_field("status"),
        filter_field("currency_code"),
        integer_field("accrued_at"),
        integer_field("amount_minor"),
    ),
}
