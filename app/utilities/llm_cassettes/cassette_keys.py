"""
Keys of recorded model calls.

A call is identified by its model, its instruction, its tools and its
transcript. The transcript is made canonical first: every payload is
re-serialized with sorted keys, and what differs from run to run although
the conversation is the same (random record ids, the per-turn fence keys
of customer text, provider tool call ids) is replaced by numbered
placeholders in order of first appearance. So the same conversation gets
the same key in every run, and two conversations that refer to the same
booking twice still differ from ones that refer to two bookings.
"""

import hashlib
import json
import re
from collections.abc import Sequence

from app.schemas.dto.conversations import LlmRequest, LlmToolDefinition
from app.schemas.dto.llm_cassettes import LlmCassetteRequest
from app.schemas.typings.conversations.strings import LlmProviderPayload
from app.schemas.typings.evaluations.constrained_strings import (
    LlmCassetteKey,
    LlmInstructionDigest,
    LlmToolsDigest,
    LlmTranscriptDigest,
)
from app.schemas.typings.evaluations.strings import LlmTranscriptTail

UUID_PATTERN: str = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# (pattern, kind): the first group, when there is one, is kept as written.
VOLATILE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(rf"\b([a-z][a-z_]*_){UUID_PATTERN}\b"), "id"),
    (re.compile(rf"\b(){UUID_PATTERN}\b"), "uuid"),
    (re.compile(r"(customer_text )[0-9a-f]{8}\b"), "fence"),
    (re.compile(r"\b(toolu_|call_|fc_)[A-Za-z0-9_\-]+\b"), "call"),
)
TRANSCRIPT_SEPARATOR: str = "\n␞\n"
MAX_TAIL_CHARACTERS: int = 1200


def canonicalize_transcript(transcript: Sequence[LlmProviderPayload]) -> list[str]:
    """Every payload in canonical form, with shared placeholder numbering."""

    placeholders: dict[str, str] = {}
    canonical: list[str] = []
    for payload in transcript:
        text: str = reserialize(str(payload))
        for pattern, kind in VOLATILE_PATTERNS:
            text = pattern.sub(PlaceholderNumbering(placeholders, kind).replace, text)

        canonical.append(text)

    return canonical


class PlaceholderNumbering:
    """Replaces a volatile token by its numbered placeholder (shared numbering)."""

    def __init__(self, placeholders: dict[str, str], kind: str) -> None:
        self._placeholders: dict[str, str] = placeholders
        self._kind: str = kind

    def replace(self, match: re.Match[str]) -> str:
        token: str = match.group(0)
        if token not in self._placeholders:
            number: int = len(self._placeholders) + 1
            self._placeholders[token] = f"{match.group(1)}<{self._kind}:{number}>"

        return self._placeholders[token]


def reserialize(payload: str) -> str:
    """A JSON payload with sorted keys; anything else as it is."""

    try:
        parsed: object = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    return json.dumps(parsed, ensure_ascii=False, sort_keys=True)


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest_tools(tools: Sequence[LlmToolDefinition]) -> LlmToolsDigest:
    """Digest of the names, descriptions and schemas, in the order offered."""

    described: list[list[str]] = [
        [
            str(tool.name),
            str(tool.description),
            reserialize(str(tool.input_schema_json)),
        ]
        for tool in tools
    ]
    return LlmToolsDigest(digest_text(json.dumps(described, ensure_ascii=False)))


def build_cassette_request(request: LlmRequest) -> LlmCassetteRequest:
    """The identity of a model call and the canonical tail of its transcript."""

    canonical: list[str] = canonicalize_transcript(request.transcript)
    instruction_digest = LlmInstructionDigest(digest_text(str(request.system_prompt)))
    tools_digest: LlmToolsDigest = digest_tools(request.tools)
    transcript_digest = LlmTranscriptDigest(
        digest_text(TRANSCRIPT_SEPARATOR.join(canonical))
    )
    key = LlmCassetteKey(
        digest_text(
            "\n".join(
                [
                    str(request.model_id),
                    str(instruction_digest),
                    str(tools_digest),
                    str(transcript_digest),
                ]
            )
        )
    )
    tail: str = canonical[-1] if canonical else ""
    return LlmCassetteRequest(
        key=key,
        model_id=request.model_id,
        instruction_digest=instruction_digest,
        tools_digest=tools_digest,
        transcript_digest=transcript_digest,
        transcript_tail=LlmTranscriptTail(tail[:MAX_TAIL_CHARACTERS]),
    )
