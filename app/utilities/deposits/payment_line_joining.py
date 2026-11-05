"""
The reply a customer reads after a turn that asked a deposit: the words
above (the assistant's own, or the engine's handoff text when the turn
failed), then each payment line send_payment_link issued, as the server
wrote it. A held booking always reaches its customer with its link, so
the hold never runs out on a customer who was never asked to pay.
"""

from collections.abc import Sequence

from app.schemas.typings.conversations.strings import MessageText

# A payment line stands apart from the words above it.
PAYMENT_LINE_SEPARATOR: str = "\n\n"


def with_payment_lines(text: MessageText, lines: Sequence[MessageText]) -> MessageText:
    """The text, then each payment line on its own paragraph (none: the text)."""

    if not lines:
        return text

    return MessageText(
        PAYMENT_LINE_SEPARATOR.join(
            [str(text).rstrip(), *(str(line) for line in lines)]
        )
    )
