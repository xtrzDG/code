from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.reply_locks import ReplyLockRegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

REPLY_LOCK_PURPOSE: str = "assistant reply"
# The other holder only reads a message or two and stores one.
REPLY_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(10)


class ReplyLockRegistry(ReplyLockRegistryContract):
    """
    One lock per assistant reply (business|reply message id), held with a
    storage transaction (`hold_with_transaction`): the holding message and
    the reply decide who says the AI disclosure under it, and their writes
    commit with the lock's release.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_for_reply(
        self, business_id: BusinessId, reply_message_id: MessageId
    ) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_transaction(
            AdvisoryLockKey(f"{REPLY_LOCK_PURPOSE}|{business_id}|{reply_message_id}"),
            REPLY_LOCK_WAIT,
        )
