import threading

from app.contracts.channels import (
    ChannelMessageReceiptRepoContract,
    ManagerTelegramLinkRepoContract,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.channel_receipts import ChannelMessageReceiptDocument
from app.schemas.domain.manager_links import ManagerTelegramLinkDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.strings import ManagerLinkCodeHash


class ChannelMessageReceiptRepository(ChannelMessageReceiptRepoContract):
    """
    Receipts keyed by business, channel and provider message id, so a
    repeated delivery finds the first receipt with one lookup (a unique key
    in a relational store).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[ChannelMessageReceiptDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            ChannelMessageReceiptDocument
        ] = collection
        self._lock: threading.Lock = threading.Lock()

    def record_if_new(self, receipt: ChannelMessageReceiptDocument) -> bool:
        receipt_key: str = build_receipt_key(receipt)
        with self._lock:
            if self._collection.get(receipt_key) is not None:
                return False

            self._collection.upsert(receipt_key, receipt)
            return True


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
        for link in self._collection.list_all():
            if link.code_hash == code_hash:
                return link

        return None

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ManagerTelegramLinkDocument]:
        return sorted(self._list(business_id), key=lambda link: link.created_at)
