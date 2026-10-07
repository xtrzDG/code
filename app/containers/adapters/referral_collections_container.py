from app.containers.adapters.client_care_collections_container import (
    ClientCareCollectionsContainer,
)
from app.containers.adapters.document_collection_provider import document_collection
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import (
    CommissionEntryDocument,
    ReferralCodeDocument,
    ReferralDocument,
)

_SIBLING = ClientCareCollectionsContainer


class ReferralCollectionsContainer(ClientCareCollectionsContainer):
    """
    The document collections of the referral and partner program (migration
    1150): partners, referral codes, referred businesses and commissions.
    It extends the client care collections (the credit ledger the rewards
    are written to lives there), so the composition root keeps one sibling
    of DocumentCollectionsContainer for both, with the same storage factory.
    """

    partner_collection = document_collection(
        PartnerDocument,
        "partners",
        _SIBLING.config,
        _SIBLING.clients,
        _SIBLING.utilities,
        _SIBLING.time_provider,
    )
    referral_code_collection = document_collection(
        ReferralCodeDocument,
        "referral_codes",
        _SIBLING.config,
        _SIBLING.clients,
        _SIBLING.utilities,
        _SIBLING.time_provider,
    )
    referral_collection = document_collection(
        ReferralDocument,
        "referrals",
        _SIBLING.config,
        _SIBLING.clients,
        _SIBLING.utilities,
        _SIBLING.time_provider,
    )
    commission_entry_collection = document_collection(
        CommissionEntryDocument,
        "commission_entries",
        _SIBLING.config,
        _SIBLING.clients,
        _SIBLING.utilities,
        _SIBLING.time_provider,
    )
