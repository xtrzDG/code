"""Keep abc order."""

from base_typed_string import BaseTypedString


class CallTranscriptText(BaseTypedString):
    """Full transcript of a phone call as delivered by the voice platform."""


class ChannelUserId(BaseTypedString):
    """
    Identifier of the customer inside a channel.

    Examples: Telegram chat id "123456789", WhatsApp "995555123456",
    web chat session key, phone call id.
    """


class LlmProviderPayload(BaseTypedString):
    """
    Raw JSON of one language-model turn exactly as it is replayed.

    Stored verbatim so the transcript stays append-only (reasoning items and
    prompt caching depend on byte-identical history).
    """


class LlmToolCallId(BaseTypedString):
    """Provider identifier of one tool call inside an assistant turn."""


class LlmToolInputJson(BaseTypedString):
    """JSON object the language model passed to a tool."""


class LlmToolResultJson(BaseTypedString):
    """JSON object returned to the language model as a tool result."""


class MessagePreview(BaseTypedString):
    """
    The beginning of a message for a list row, cut at a word boundary with
    an ellipsis when the message is longer.
    """


class MessageText(BaseTypedString):
    """Text of one message."""


class ProviderCallId(BaseTypedString):
    """Call identifier at the voice platform or telephony provider."""


class RecordingStoragePath(BaseTypedString):
    """Path of a call recording in EU object storage."""


class UnverifiedReplyValue(BaseTypedString):
    """
    Money amount, time, date, phone or number in an assistant reply, as
    written, that neither the facts, the tool results nor the customer's
    messages support (invented-numbers guard).
    """


# Keep abc order for all non example types, if possible.
