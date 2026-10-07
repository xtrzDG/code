"""Asking the cheap model what one conversation was about."""

import logging

from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import MessageDocument
from app.schemas.dto.conversations import LlmCallLimits, LlmRequest, LlmResponse
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallRetryLimit,
    LlmCallTimeoutSeconds,
    LlmMaxOutputTokens,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.media.attachment_texts import readable_message_text
from app.utilities.memory.conversation_summary_prompt import (
    CONVERSATION_SUMMARY_SYSTEM_PROMPT,
    build_summary_request_text,
    read_conversation_summary,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
SUMMARY_OUTPUT_TOKENS: LlmMaxOutputTokens = LlmMaxOutputTokens(400)
SUMMARY_CALL_LIMITS: LlmCallLimits = LlmCallLimits(
    timeout_seconds=LlmCallTimeoutSeconds(30),
    retry_limit=LlmCallRetryLimit(1),
)


def transcript_lines(
    messages: list[MessageDocument],
) -> list[tuple[MessageAuthor, str]]:
    """The conversation's messages as the model reads them, in time order."""

    return [
        (
            message.author,
            readable_message_text(str(message.text), message.attachments)
            if message.direction is MessageDirection.INBOUND
            else str(message.text),
        )
        for message in sorted(messages, key=lambda item: int(item.created_at))
    ]


def has_customer_words(lines: list[tuple[MessageAuthor, str]]) -> bool:
    return any(
        author is MessageAuthor.CUSTOMER and text.strip() for author, text in lines
    )


def ask_for_summary(
    llm_adapter: LlmAdapterContract,
    model_id: LlmModelId,
    business: BusinessDocument,
    lines: list[tuple[MessageAuthor, str]],
) -> ConversationSummaryText | None:
    """
    The model's summary, None when it wrote nothing readable.

    Raises:
        ExternalServiceError, LlmRefusedError: the model call failed.
    """

    response: LlmResponse = llm_adapter.complete(
        LlmRequest(
            model_id=model_id,
            system_prompt=SystemPromptText(CONVERSATION_SUMMARY_SYSTEM_PROMPT),
            tools=[],
            transcript=[
                llm_adapter.build_user_text_turn(
                    MessageText(build_summary_request_text(str(business.name), lines))
                )
            ],
            max_output_tokens=SUMMARY_OUTPUT_TOKENS,
            effort=LlmEffort.LOW,
            call_limits=SUMMARY_CALL_LIMITS,
        )
    )
    summary: ConversationSummaryText | None = read_conversation_summary(
        None if response.text is None else str(response.text)
    )
    if summary is None:
        LOGGER.warning("The model wrote no readable conversation summary.")

    return summary
