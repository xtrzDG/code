"""The partners of the referral program (migration 1150)."""

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.referral_repositories import PartnerRepoContract
from app.repositories.document_queries import field_equals
from app.schemas.constants.referrals import PartnerStatus
from app.schemas.domain.partners import PartnerDocument
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText
from app.schemas.typings.users.constrained_strings import EmailAddress

PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("phone_number")
EMAIL_FIELD: DocumentFieldPath = DocumentFieldPath("email")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")


class PartnerRepository(PartnerRepoContract):
    """Partners keyed by id (derived from their sign-in destination)."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[PartnerDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PartnerDocument] = (
            collection
        )

    def add(self, partner: PartnerDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(partner.id), partner))

    def save(self, partner: PartnerDocument) -> None:
        self._collection.upsert(str(partner.id), partner)

    def get(self, partner_id: PartnerId) -> PartnerDocument | None:
        return self._collection.get(str(partner_id))

    def get_many(self, partner_ids: list[PartnerId]) -> list[PartnerDocument]:
        return self._collection.get_many([str(partner_id) for partner_id in partner_ids])

    def find_by_phone_number(
        self, phone_number: E164PhoneNumber
    ) -> PartnerDocument | None:
        return self._collection.find_one_by_field(
            PHONE_NUMBER_FIELD, DocumentFieldText(str(phone_number))
        )

    def find_by_email(self, email: EmailAddress) -> PartnerDocument | None:
        return self._collection.find_one_by_field(
            EMAIL_FIELD, DocumentFieldText(str(email))
        )

    def list_partners(self) -> list[PartnerDocument]:
        return [
            partner
            for status in PartnerStatus
            for partner in self._collection.list_by_fields(
                (field_equals(STATUS_FIELD, status),)
            )
        ]
