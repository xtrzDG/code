"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString

SHA256_HEX_PATTERN: str = r"^[0-9a-f]{64}$"


class LlmInstructionDigest(BaseConstrainedTypedString):
    """
    SHA-256 of the system prompt of a model call.

    Example:
        digest = LlmInstructionDigest("0" * 64)
    """

    min_length = 64
    max_length = 64
    pattern = SHA256_HEX_PATTERN


class LlmRequestDigest(BaseConstrainedTypedString):
    """
    Digest of one recorded model call: the SHA-256 of its model, instruction,
    tools and transcript digests.

    Example:
        request_digest = LlmRequestDigest("0" * 64)
    """

    min_length = 64
    max_length = 64
    pattern = SHA256_HEX_PATTERN


class LlmToolsDigest(BaseConstrainedTypedString):
    """
    SHA-256 of the tool definitions offered in a model call.

    Example:
        digest = LlmToolsDigest("0" * 64)
    """

    min_length = 64
    max_length = 64
    pattern = SHA256_HEX_PATTERN


class LlmTranscriptDigest(BaseConstrainedTypedString):
    """
    SHA-256 of the canonical transcript of a model call (random ids, fence
    keys and tool call ids replaced by placeholders).

    Example:
        digest = LlmTranscriptDigest("0" * 64)
    """

    min_length = 64
    max_length = 64
    pattern = SHA256_HEX_PATTERN


class ToolInputFieldName(BaseConstrainedTypedString):
    """
    Name of one input field of a model tool call, e.g. "party_size".

    Example:
        field = ToolInputFieldName("party_size")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"
