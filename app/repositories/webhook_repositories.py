from typed_time_provider import Microseconds

from app.contracts.repositories.integration_repositories import (
    WebhookDeliveryChange,
    WebhookDeliveryRepoContract,
    WebhookEndpointChange,
    WebhookEndpointRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    ascending,
    field_equals,
    time_range,
)
from app.schemas.constants.integrations import WebhookEndpointStatus
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.integrations.prefixed_id import (
    WebhookDeliveryId,
    WebhookEndpointId,
)
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")
ENDPOINT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("endpoint_id")
EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("expires_at")
CONTACT_ID_FIELD: DocumentFieldPath = DocumentFieldPath("contact_id")
# A business keeps a handful of endpoints (the cabinet caps them); a list
# never reads more than this.
ENDPOINT_LIST_LIMIT: DocumentQueryLimit = DocumentQueryLimit(100)


class WebhookEndpointRepository(
    BusinessScopedRepository[WebhookEndpointDocument],
    WebhookEndpointRepoContract,
):
    """
    Webhook endpoints, read by business and id, the business's list in
    creation order and its ACTIVE ones (indexed by status, migration 1181).
    """

    def save(self, endpoint: WebhookEndpointDocument) -> None:
        self._store(str(endpoint.id), endpoint)

    def get(
        self, business_id: BusinessId, endpoint_id: WebhookEndpointId
    ) -> WebhookEndpointDocument | None:
        return self._load(business_id, str(endpoint_id))

    def update(
        self,
        business_id: BusinessId,
        endpoint_id: WebhookEndpointId,
        change: WebhookEndpointChange,
    ) -> WebhookEndpointDocument | None:
        return self._modify_in_business(business_id, str(endpoint_id), change)

    def delete(self, business_id: BusinessId, endpoint_id: WebhookEndpointId) -> None:
        self._remove(business_id, str(endpoint_id))

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[WebhookEndpointDocument]:
        return self._list_in_business(
            business_id, order=ascending(CREATED_AT_FIELD), limit=ENDPOINT_LIST_LIMIT
        )

    def list_active(self, business_id: BusinessId) -> list[WebhookEndpointDocument]:
        return self._list_in_business(
            business_id,
            [field_equals(STATUS_FIELD, WebhookEndpointStatus.ACTIVE)],
            limit=ENDPOINT_LIST_LIMIT,
        )


class WebhookDeliveryRepository(
    BusinessScopedRepository[WebhookDeliveryDocument],
    WebhookDeliveryRepoContract,
):
    """
    Deliveries of events to endpoints, keyed by the id derived from the
    endpoint and the event (an insert that finds the id taken writes
    nothing); an endpoint's log newest first, the purge by `expires_at`
    across businesses and a contact's deliveries for an erasure (indexed,
    migration 1181).
    """

    def insert_if_new(self, delivery: WebhookDeliveryDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(delivery.id), delivery)

    def get(
        self, business_id: BusinessId, delivery_id: WebhookDeliveryId
    ) -> WebhookDeliveryDocument | None:
        return self._load(business_id, str(delivery_id))

    def update(
        self,
        business_id: BusinessId,
        delivery_id: WebhookDeliveryId,
        change: WebhookDeliveryChange,
    ) -> WebhookDeliveryDocument | None:
        return self._modify_in_business(business_id, str(delivery_id), change)

    def page_of_endpoint(
        self,
        business_id: BusinessId,
        endpoint_id: WebhookEndpointId,
        window: KeysetSlice,
    ) -> list[WebhookDeliveryDocument]:
        return self._page_in_business(
            business_id,
            (CREATED_AT_FIELD,),
            window,
            where=DocumentFilter(
                matches=(field_equals(ENDPOINT_ID_FIELD, endpoint_id),)
            ),
        )

    def delete_expired_before(self, moment: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(EXPIRES_AT_FIELD, ending_before=moment)
        )

    def delete_of_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> DocumentCount:
        deliveries = self._list_in_business(
            business_id, (field_equals(CONTACT_ID_FIELD, contact_id),)
        )
        for delivery in deliveries:
            self._collection.delete(str(delivery.id))
        return DocumentCount(len(deliveries))
