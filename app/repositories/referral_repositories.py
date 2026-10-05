"""
Referral codes and referred businesses (migration 1150): codes keyed by
the code itself, so a code names one partner or business; a partner's
referrals newest first, an owner's invitations through the business
column.
"""

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.referral_repositories import (
    ReferralCodeRepoContract,
    ReferralRepoContract,
)
from app.repositories.document_queries import (
    document_position,
    field_equals,
    of_business,
)
from app.schemas.domain.referrals import ReferralCodeDocument, ReferralDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_pages import DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.referrals.constrained_integers import ReferredBusinessCount
from app.schemas.typings.referrals.prefixed_id import (
    PartnerId,
    ReferralCodeId,
    ReferralId,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

PARTNER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("partner_id")
REFERRED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("referred_at")
FIRST_PAID_AT_FIELD: DocumentFieldPath = DocumentFieldPath("first_paid_at")


class ReferralCodeRepository(ReferralCodeRepoContract):
    """Referral codes keyed by their id (derived from the code in lower case)."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[ReferralCodeDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[ReferralCodeDocument] = (
            collection
        )

    def claim(self, code: ReferralCodeDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(code.id), code))

    def get(self, code_id: ReferralCodeId) -> ReferralCodeDocument | None:
        return self._collection.get(str(code_id))

    def list_by_partner(self, partner_id: PartnerId) -> list[ReferralCodeDocument]:
        return self._collection.list_by_fields(
            (field_equals(PARTNER_ID_FIELD, partner_id),)
        )


class ReferralRepository(ReferralRepoContract):
    """Referred businesses keyed by id (derived from the referred business)."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[ReferralDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[ReferralDocument] = (
            collection
        )

    def record(self, referral: ReferralDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(referral.id), referral))

    def get(self, referral_id: ReferralId) -> ReferralDocument | None:
        return self._collection.get(str(referral_id))

    def save(self, referral: ReferralDocument) -> None:
        self._collection.upsert(str(referral.id), referral)

    def page_by_partner(
        self, partner_id: PartnerId, window: KeysetSlice
    ) -> list[ReferralDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(
                    matches=(field_equals(PARTNER_ID_FIELD, partner_id),)
                ),
                sort_fields=(REFERRED_AT_FIELD,),
                after=document_position(window.after),
                limit=DocumentQueryLimit(int(window.limit)),
            )
        )

    def count_by_partner(
        self, partner_id: PartnerId, *, only_paid: bool = False
    ) -> ReferredBusinessCount:
        return ReferredBusinessCount(
            int(
                self._collection.count_by_fields(
                    (field_equals(PARTNER_ID_FIELD, partner_id),),
                    within=(
                        DocumentFieldRange(
                            field=FIRST_PAID_AT_FIELD,
                            lower=DocumentFieldInteger(0),
                        )
                        if only_paid
                        else None
                    ),
                )
            )
        )

    def list_invited_by(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[ReferralDocument]:
        return self._collection.list_by_fields((of_business(business_id),), limit=limit)
