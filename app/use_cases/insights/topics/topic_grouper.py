"""Asking a cheap language model to group one language's items into topics."""

import logging
from collections.abc import Sequence

from app.contracts.llm import LlmAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmEffort
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.conversations import LlmCallLimits, LlmRequest, LlmResponse
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallRetryLimit,
    LlmCallTimeoutSeconds,
    LlmMaxOutputTokens,
)
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.insights.constrained_strings import TopicLabel
from app.utilities.value.topic_batches import TopicBatch
from app.utilities.value.topic_grouping import (
    TOPIC_SYSTEM_PROMPT,
    GroupedTopic,
    build_topic_request_text,
    read_grouped_topics,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
TOPIC_OUTPUT_TOKENS: LlmMaxOutputTokens = LlmMaxOutputTokens(3000)
TOPIC_CALL_LIMITS: LlmCallLimits = LlmCallLimits(
    timeout_seconds=LlmCallTimeoutSeconds(60),
    retry_limit=LlmCallRetryLimit(1),
)


class TopicGrouper:
    """
    Groups one batch with a cheap model (LLM_SUMMARY_MODEL_ID, else the
    chat model) at low effort; the labels are written in the owner's
    language, and the previous night's labels are offered so a topic keeps
    its name. A provider error or an unreadable answer gives None (the
    stored topics stay until the next try).
    """

    def __init__(
        self,
        llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
    ) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._app_settings: AppSettings = app_settings

    def group(
        self,
        business: BusinessDocument,
        batch: TopicBatch,
        previous_labels: Sequence[TopicLabel],
    ) -> list[GroupedTopic] | None:
        request = LlmRequest(
            model_id=(
                self._app_settings.llm_summary_model_id
                or self._app_settings.llm_model_id
            ),
            system_prompt=SystemPromptText(TOPIC_SYSTEM_PROMPT),
            tools=[],
            transcript=[
                self._llm_adapter.build_user_text_turn(
                    MessageText(
                        build_topic_request_text(
                            str(business.owner_language),
                            str(business.name),
                            [str(label) for label in previous_labels],
                            batch.first_messages,
                            batch.open_questions,
                        )
                    )
                )
            ],
            max_output_tokens=TOPIC_OUTPUT_TOKENS,
            effort=LlmEffort.LOW,
            call_limits=TOPIC_CALL_LIMITS,
        )
        try:
            response: LlmResponse = self._llm_adapter.complete(request)
        except ApplicationError as error:
            LOGGER.warning("Grouping the topics of %s failed: %s", business.id, error)
            return None

        topics: list[GroupedTopic] | None = read_grouped_topics(
            None if response.text is None else str(response.text),
            len(batch.first_messages),
            len(batch.open_questions),
        )
        if topics is None:
            LOGGER.warning("The model grouped no readable topics for %s.", business.id)

        return topics
