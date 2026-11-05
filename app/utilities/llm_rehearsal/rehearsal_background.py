"""
The rehearsal's answers to the platform's own background requests
(LLM_PROVIDER=scripted): grouping what customers ask about, and the
customer memory's summary of a conversation (what the customer first
wrote, so a returning customer's memory reads true on a development
server).
"""

import re

from app.schemas.dto.conversations import LlmRequest
from app.utilities.llm_rehearsal.rehearsal_reading import read_texts
from app.utilities.llm_rehearsal.rehearsal_topics import rehearse_topics
from app.utilities.memory.conversation_summary_prompt import (
    CONVERSATION_SUMMARY_SYSTEM_PROMPT,
)
from app.utilities.value.topic_grouping import TOPIC_SYSTEM_PROMPT

CUSTOMER_LINE: re.Pattern[str] = re.compile(r"^Customer: (.+)$", re.M)
MAX_QUOTED_CHARACTERS: int = 200
EMPTY_CONVERSATION_SUMMARY: str = "The customer wrote without a request."


def rehearse_background_task(request: LlmRequest) -> str | None:
    """The answer to a background request, None for the assistant's turns."""

    prompt: str = str(request.system_prompt)
    if prompt == TOPIC_SYSTEM_PROMPT:
        return rehearse_topics(read_texts(request.transcript[-1]))

    if prompt == CONVERSATION_SUMMARY_SYSTEM_PROMPT:
        return rehearse_summary(read_texts(request.transcript[-1]))

    return None


def rehearse_summary(request_text: str) -> str:
    """ "The customer wrote: “A table for 2 tonight?”" from their first line."""

    first: re.Match[str] | None = CUSTOMER_LINE.search(request_text)
    if first is None:
        return EMPTY_CONVERSATION_SUMMARY

    words: str = first.group(1).strip()
    if len(words) > MAX_QUOTED_CHARACTERS:
        words = words[: MAX_QUOTED_CHARACTERS - 1].rstrip() + "…"

    return f"The customer wrote: “{words}”"
