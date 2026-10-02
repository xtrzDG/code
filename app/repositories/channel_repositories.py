from typed_time_provider import Microseconds

from app.contracts.channels import (
    ChannelMessageReceiptRepoContract,
    ManagerTelegramLinkRepoContract,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import time_range
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ManagerLinkCodeHash
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.strings import DocumentFieldText

RECEIPT_CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")
CODE_HASH_FIELD: DocumentFieldPath = DocumentFieldPath("code_hash")


class ChannelMessageReceiptRepository(ChannelMessageReceiptRepoContract):
    """
    Receipts keyed by business, channel and provider message id. A receipt
    is inserted in one atomic step that fails on a taken key (and, on
    Postgres, on the unique index of the same three values), so two
    deliveries of one message are never both accepted, not even by two
    instances at the same moment.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ChannelMessageReceiptDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            ChannelMessageReceiptDocument
        ] = collection

    def record_if_new(self, receipt: ChannelMessageReceiptDocument) -> bool:
        return self._collection.insert_if_absent(build_receipt_key(receipt), receipt)

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(RECEIPT_CREATED_AT_FIELD, ending_before=created_before)
        )


def build_receipt_key(receipt: ChannelMessageReceiptDocument) -> str:
    return (
        f"{receipt.business_id}:{receipt.channel.value}:{receipt.provider_message_id}"
    )


class ManagerTelegramLinkRepository(
    BusinessScopedRepository[ManagerTelegramLinkDocument],
    ManagerTelegramLinkRepoContract,
):
    def save(self, link: ManagerTelegramLinkDocument) -> None:
        self._store(str(link.id), link)

    def find_by_code_hash(
        self,
        code_hash: ManagerLinkCodeHash,
    ) -> ManagerTelegramLinkDocument | None:
        return self._collection.find_one_by_field(
            CODE_HASH_FIELD, DocumentFieldText(str(code_hash))
        )

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ManagerTelegramLinkDocument]:
        return sorted(
            self._list_in_business(business_id), key=lambda link: link.created_at
        )
