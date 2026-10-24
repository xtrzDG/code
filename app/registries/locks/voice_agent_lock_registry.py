from contextlib import AbstractContextManager

from app.contracts.locks import AdvisoryLockAdapterContract
from app.contracts.voice_platform import VoiceAgentLockRegistryContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_integers import LockWaitSeconds
from app.schemas.typings.storage.constrained_strings import AdvisoryLockKey

VOICE_AGENT_LOCK_PURPOSE: str = "voice-agent"


class VoiceAgentLockRegistry(VoiceAgentLockRegistryContract):
    """
    One lock per business around setting up its voice agent: held by a
    connection of its own for the block (`hold_with_session`), since the
    block calls the voice platform for seconds and its storage writes
    commit on their own; released when the block ends or its process dies.
    """

    def __init__(self, advisory_locks: AdvisoryLockAdapterContract) -> None:
        self._advisory_locks: AdvisoryLockAdapterContract = advisory_locks

    def lock_agent(
        self, business_id: BusinessId, wait: LockWaitSeconds
    ) -> AbstractContextManager[object]:
        return self._advisory_locks.hold_with_session(
            AdvisoryLockKey(f"{VOICE_AGENT_LOCK_PURPOSE}|{business_id}"), wait
        )
