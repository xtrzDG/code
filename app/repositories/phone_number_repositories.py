from app.contracts.phone_numbers import (
    PhoneNumberChange,
    PhoneNumberRepoContract,
    PhoneNumberRequestRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals
from app.schemas.constants.phone_numbers import (
    PhoneNumberRequestStatus,
    PhoneNumberStatus,
)
from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.schemas.dto.storage_pages import DocumentPagePosition, DocumentPageQuery
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.schemas.typings.telephony.constrained_strings import RentedLineNumber
from app.schemas.typings.telephony.prefixed_id import PhoneNumberId
from app.utilities.telephony.phone_number_keys import phone_number_request_id_of

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
PHONE_NUMBER_FIELD: DocumentFieldPath = DocumentFieldPath("phone_number")
BILLED_UNTIL_FIELD: DocumentFieldPath = DocumentFieldPath("billed_until")
HELD_STATUSES: tuple[PhoneNumberStatus, ...] = (
    PhoneNumberStatus.ACTIVE,
    PhoneNumberStatus.RELEASING,
)


class PhoneNumberRepository(
    BusinessScopedRepository[PhoneNumberDocument],
    PhoneNumberRepoContract,
):
    """
    Numbers rented for businesses (1213), keyed by their id. A business's
    numbers are read by its own column; the jobs ask across businesses by
    status (and when the next rental month begins), a purchase by number.
    """

    def save(self, number: PhoneNumberDocument) -> None:
        self._store(str(number.id), number)

    def get(
        self, business_id: BusinessId, number_id: PhoneNumberId
    ) -> PhoneNumberDocument | None:
        return self._load(business_id, str(number_id))

    def find_held(self, business_id: BusinessId) -> PhoneNumberDocument | None:
        for status in HELD_STATUSES:
            held: PhoneNumberDocument | None = self._find_in_business(
                business_id, [field_equals(STATUS_FIELD, status)]
            )
            if held is not None:
                return held

        return None

    def find_holder(self, phone_number: RentedLineNumber) -> PhoneNumberDocument | None:
        for number in self._collection.list_by_fields(
            [field_equals(PHONE_NUMBER_FIELD, phone_number)]
        ):
            if number.status in HELD_STATUSES:
                return number

        return None

    def page_in_status(
        self,
        status: PhoneNumberStatus,
        after: PhoneNumberDocument | None,
        limit: DocumentQueryLimit,
    ) -> list[PhoneNumberDocument]:
        return self._collection.page_by(
            DocumentPageQuery(
                where=DocumentFilter(matches=(field_equals(STATUS_FIELD, status),)),
                sort_fields=(BILLED_UNTIL_FIELD,),
                is_descending=False,
                after=None
                if after is None
                else DocumentPagePosition(
                    values=(DocumentFieldInteger(int(after.billed_until)),),
                    document_key=StoredDocumentKey(str(after.id)),
                ),
                limit=limit,
            )
        )

    def modify(
        self,
        business_id: BusinessId,
        number_id: PhoneNumberId,
        change: PhoneNumberChange,
    ) -> PhoneNumberDocument | None:
        return self._modify_in_business(business_id, str(number_id), change)


class PhoneNumberRequestRepository(
    BusinessScopedRepository[PhoneNumberRequestDocument],
    PhoneNumberRequestRepoContract,
):
    """
    Requests for numbers the platform team arranges (1213): one document per
    business under its derived id, opened again when the owner asks again.
    """

    def get_by_business(
        self, business_id: BusinessId
    ) -> PhoneNumberRequestDocument | None:
        return self._load(business_id, str(phone_number_request_id_of(business_id)))

    def open_request(self, request: PhoneNumberRequestDocument) -> bool:
        if self._collection.insert_if_absent(str(request.id), request):
            return True

        def reopen(
            stored: PhoneNumberRequestDocument,
        ) -> PhoneNumberRequestDocument | None:
            if stored.status is PhoneNumberRequestStatus.OPEN:
                return None

            return request.model_copy(update={"created_at": stored.created_at})

        return (
            self._modify_in_business(request.business_id, str(request.id), reopen)
            is not None
        )

    def save(self, request: PhoneNumberRequestDocument) -> None:
        self._store(str(request.id), request)

    def list_open(self, limit: DocumentQueryLimit) -> list[PhoneNumberRequestDocument]:
        return self._collection.list_by_fields(
            [field_equals(STATUS_FIELD, PhoneNumberRequestStatus.OPEN)], limit=limit
        )
