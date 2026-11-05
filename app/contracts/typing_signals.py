"""The "typing…" a customer sees while the assistant writes the reply."""

from contextlib import AbstractContextManager
from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.dto.channels.typing_signals import TypingRequest


class TypingSignalFacilitatorContract(FacilitatorContract, Protocol):
    """
    Typing signals never fail a turn: a channel that cannot show typing,
    a disconnected channel or a refused signal only leaves a log line.
    """

    def signal_once(self, request: TypingRequest) -> None:
        """Show "typing…" now (the platform hides it after a few seconds)."""
        raise NotImplementedError

    def keep_typing(self, request: TypingRequest) -> AbstractContextManager[None]:
        """
        Show "typing…" at once and again before the platform hides it,
        until the block ends. The channel is read when the block starts
        (in the caller's storage scope); the signals go out from a thread
        of their own, so a slow platform never delays the reply.
        """
        raise NotImplementedError
