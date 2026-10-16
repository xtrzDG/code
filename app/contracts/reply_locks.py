"""The lock around what is stored for one assistant reply."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.registry_contract import RegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId


class ReplyLockRegistryContract(RegistryContract, Protocol):
    def lock_for_reply(
        self, business_id: BusinessId, reply_message_id: MessageId
    ) -> AbstractContextManager[object]:
        """
        Lock serializing what is stored for one assistant reply across
        every process: the "one moment" a slow turn sends from its deadline
        thread and the reply the turn itself records. A short block of
        storage reads and writes that commit with the lock's release, so
        the second holder sees the first one's message (the AI disclosure
        is said once, by whichever comes first).
        """
        raise NotImplementedError
