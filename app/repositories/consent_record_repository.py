from app.contracts.repositories.consent_repositories import ConsentRecordRepoContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    ascending,
    field_equals,
)
from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")


class ConsentRecordRepository(
    BusinessScopedRepository[ConsentRecordDocument], ConsentRecordRepoContract
):
    """
    The consent ledger: entries are only ever inserted (never an upsert,
    which would need the UPDATE the database refuses the application,
    1246), and read by customer in the order they were written.
    """

    def append(self, record: ConsentRecordDocument) -> None:
        self._collection.insert_if_absent(str(record.id), record)

    def list_by_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> list[ConsentRecordDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(CONTACT_ID_FIELD, contact_id)],
            order=ascending(CREATED_AT_FIELD),
        )
