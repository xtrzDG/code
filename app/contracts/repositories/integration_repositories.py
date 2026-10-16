"""
Persistence contracts of the public API and outbound webhooks (1181):
webhook endpoints, their deliveries and API keys. Every read names the
business, except finding the key of a request by its hash (across
businesses, platform-wide) and the purge of expired deliveries.
"""

from collections.abc import Callable
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.integrations.constrained_strings import ApiKeySecretHash
from app.schemas.typings.integrations.prefixed_id import (
    ApiKeyId,
    WebhookDeliveryId,
    WebhookEndpointId,
)
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount

type WebhookEndpointChange = Callable[
    [WebhookEndpointDocument], WebhookEndpointDocument | None
]
type WebhookDeliveryChange = Callable[
    [WebhookDeliveryDocument], WebhookDeliveryDocument | None
]
type ApiKeyChange = Callable[[ApiKeyDocument], ApiKeyDocument | None]


class WebhookEndpointRepoContract(RepoContract, Protocol):
    def save(self, endpoint: WebhookEndpointDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, endpoint_id: WebhookEndpointId
    ) -> WebhookEndpointDocument | None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        endpoint_id: WebhookEndpointId,
        change: WebhookEndpointChange,
    ) -> WebhookEndpointDocument | None:
        """What `change` made of the stored endpoint, written in one step."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, endpoint_id: WebhookEndpointId) -> None:
        raise NotImplementedError

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[WebhookEndpointDocument]:
        """Every endpoint of the business, oldest first (a business has few)."""
        raise NotImplementedError

    def list_active(self, business_id: BusinessId) -> list[WebhookEndpointDocument]:
        """The ACTIVE endpoints: where an announced change goes (indexed)."""
        raise NotImplementedError


class WebhookDeliveryRepoContract(RepoContract, Protocol):
    def insert_if_new(self, delivery: WebhookDeliveryDocument) -> IsDocumentInserted:
        """Store a new delivery; False when one with its id exists already."""
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, delivery_id: WebhookDeliveryId
    ) -> WebhookDeliveryDocument | None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        delivery_id: WebhookDeliveryId,
        change: WebhookDeliveryChange,
    ) -> WebhookDeliveryDocument | None:
        raise NotImplementedError

    def page_of_endpoint(
        self,
        business_id: BusinessId,
        endpoint_id: WebhookEndpointId,
        window: KeysetSlice,
    ) -> list[WebhookDeliveryDocument]:
        """An endpoint's deliveries, newest first (the delivery log)."""
        raise NotImplementedError

    def delete_expired_before(self, moment: Microseconds) -> DocumentCount:
        """Across businesses: delete deliveries whose 30 days ended before then."""
        raise NotImplementedError

    def delete_of_contact(
        self, business_id: BusinessId, contact_id: ContactId
    ) -> DocumentCount:
        """Delete the deliveries whose payload describes the contact (erasure)."""
        raise NotImplementedError


class ApiKeyRepoContract(RepoContract, Protocol):
    def save(self, api_key: ApiKeyDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, api_key_id: ApiKeyId
    ) -> ApiKeyDocument | None:
        raise NotImplementedError

    def update(
        self, business_id: BusinessId, api_key_id: ApiKeyId, change: ApiKeyChange
    ) -> ApiKeyDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ApiKeyDocument]:
        """Every key of the business, oldest first (a business has few)."""
        raise NotImplementedError

    def find_by_secret_hash(
        self, secret_hash: ApiKeySecretHash
    ) -> ApiKeyDocument | None:
        """Across businesses (platform-wide scope): the key a request names."""
        raise NotImplementedError
