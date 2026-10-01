"""Keep abc order."""

from base_typed_string import BaseTypedString


class ChannelUserId(BaseTypedString):
    """
    Identifier of the customer inside a channel.

    Examples: Telegram chat id "123456789", WhatsApp "995555123456",
    web chat session key, phone call id.
    """


class CustomerName(BaseTypedString):
    """Name the customer gave or the channel reported."""


class LlmProviderPayload(BaseTypedString):
    """
    Raw JSON of one language-model turn exactly as the provider expects it back.

    Stored verbatim so the transcript stays append-only (thinking blocks and
    prompt caching depend on byte-identical history).
    """


class LlmToolCallId(BaseTypedString):
    """Provider identifier of one tool call inside an assistant turn."""


class LlmToolInputJson(BaseTypedString):
    """JSON object the language model passed to a tool."""


class LlmToolResultJson(BaseTypedString):
    """JSON object returned to the language model as a tool result."""


class MessageText(BaseTypedString):
    """Text of one customer-visible message."""


# Keep abc order for all non example types, if possible.
