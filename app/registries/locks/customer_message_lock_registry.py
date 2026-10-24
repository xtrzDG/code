from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.registries import CustomerMessageLockRegistryContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

CUSTOMER_MESSAGE_LOCK_PURPOSE: str = "customer messages"
# A turn makes a few model calls of at most LLM_CALL_TIMEOUT_SECONDS each
# (a retry included); the next message of the customer waits for it, but
# not longer than the inbox lease of the job that carries it (180 s).
CUSTOMER_MESSAGE_LOCK_WAIT: LockWaitSeconds = LockWaitSeconds(150)


class CustomerMessageLockRegistry(CustomerMessageLockRegistryContract):
    """
    One lock per customer in one channel of one business
    (business|channel|channel user id), held for a whole turn: the widget
    answered by any API instance and the inbox answered by any worker take
    the same lock, so a customer's messages are answered one at a time,
    each reply sees the previous one and transcript turns keep consecutive
    numbers. Different customers run in parallel.

    The lock is session-held (`hold_with_session`): a turn calls the model,
    so no storage transaction stays open across it.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_for_customer(
        self,
        business_id: BusinessId,
        channel: ChannelKind,
        channel_user_id: ChannelUserId,
    ) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_session(
            AdvisoryLockKey(
                f"{CUSTOMER_MESSAGE_LOCK_PURPOSE}|{business_id}|"
                f"{channel.value}|{channel_user_id}"
            ),
            CUSTOMER_MESSAGE_LOCK_WAIT,
        )
