from collections.abc import Generator
from contextlib import contextmanager, nullcontext

from typed_time_provider import Microseconds

from app.contracts.typing_signals import TypingSignalFacilitatorContract
from app.orchestrators.channels.inbox.turn_deadline_watch import TurnDeadlineWatch
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.channels.typing_signals import TypingRequest


class CustomerWait:
    """
    What a customer sees while their reply is written: "typing…" at once
    and until the reply is ready (Telegram, WhatsApp, Messenger, Instagram;
    the website widget shows its own), and the "one moment" of a turn past
    its deadline (`TurnDeadlineWatch`).
    """

    def __init__(
        self,
        typing_signals: TypingSignalFacilitatorContract,
        deadline_watch: TurnDeadlineWatch,
    ) -> None:
        self._typing_signals: TypingSignalFacilitatorContract = typing_signals
        self._deadline_watch: TurnDeadlineWatch = deadline_watch

    def acknowledge(self, event: InboundEventDocument) -> None:
        """One "typing…" for a message whose answer comes a little later."""

        request: TypingRequest | None = typing_request(event)
        if request is not None:
            self._typing_signals.signal_once(request)

    @contextmanager
    def while_answering(
        self, event: InboundEventDocument, waiting_since: Microseconds
    ) -> Generator[None]:
        """
        Typing and the turn deadline while `event` (the last message of the
        customer's burst, waiting since `waiting_since`) is answered.
        """

        request: TypingRequest | None = typing_request(event)
        with (
            nullcontext()
            if request is None
            else self._typing_signals.keep_typing(request),
            self._deadline_watch.watch(event, waiting_since),
        ):
            yield


def typing_request(event: InboundEventDocument) -> TypingRequest | None:
    """Whom the "typing…" of an event's reply goes to."""

    if event.business_id is None or event.customer_message is None:
        return None

    return TypingRequest(
        business_id=event.business_id,
        channel=event.channel,
        channel_id=event.channel_id,
        channel_user_id=event.customer_message.channel_user_id,
        replying_to=event.provider_message_id,
    )
