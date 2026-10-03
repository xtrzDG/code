"""Asking the language model for the summaries of one call."""

import logging

from app.contracts.llm import LlmAdapterContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmEffort
from app.schemas.constants.conversations import CallOutcome, MessageAuthor
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.conversations import CallSummary
from app.schemas.dto.conversations import LlmCallLimits, LlmRequest, LlmResponse
from app.schemas.dto.voice_webhooks import FinishedCallTranscriptLine
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallRetryLimit,
    LlmCallTimeoutSeconds,
    LlmMaxOutputTokens,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.calls.call_summary_prompt import (
    CALL_SUMMARY_SYSTEM_PROMPT,
    build_call_summary_request_text,
    read_call_summaries,
)

LOGGER: logging.Logger = logging.getLogger(__name__)
# The owner's language first, then the staff contacts' and devices'; a
# summary in more languages costs more and helps nobody.
MAX_SUMMARY_LANGUAGES: int = 4
SUMMARY_OUTPUT_TOKENS: LlmMaxOutputTokens = LlmMaxOutputTokens(2000)
SUMMARY_CALL_LIMITS: LlmCallLimits = LlmCallLimits(
    timeout_seconds=LlmCallTimeoutSeconds(30),
    retry_limit=LlmCallRetryLimit(1),
)


class CallSummaryWriter:
    """
    Writes the summaries of a call with a cheap model (LLM_SUMMARY_MODEL_ID,
    else the chat model) at low effort. A call where the caller never spoke
    has nothing to summarize; a provider error or an unreadable answer
    leaves the call without a summary (staff still get the call's facts).
    """

    def __init__(
        self,
        llm_adapter: LlmAdapterContract,
        app_settings: AppSettings,
    ) -> None:
        self._llm_adapter: LlmAdapterContract = llm_adapter
        self._app_settings: AppSettings = app_settings

    def write(
        self,
        business: BusinessDocument,
        outcome: CallOutcome | None,
        transcript: list[FinishedCallTranscriptLine],
        languages: list[LanguageTag],
    ) -> list[CallSummary]:
        if not languages or not any(
            line.author is MessageAuthor.CUSTOMER for line in transcript
        ):
            return []

        request = LlmRequest(
            model_id=self._model_id(),
            system_prompt=SystemPromptText(CALL_SUMMARY_SYSTEM_PROMPT),
            tools=[],
            transcript=[
                self._llm_adapter.build_user_text_turn(
                    MessageText(
                        build_call_summary_request_text(
                            str(business.name), outcome, languages, transcript
                        )
                    )
                )
            ],
            max_output_tokens=SUMMARY_OUTPUT_TOKENS,
            effort=LlmEffort.LOW,
            call_limits=SUMMARY_CALL_LIMITS,
        )
        try:
            response: LlmResponse = self._llm_adapter.complete(request)
        except ApplicationError:
            LOGGER.exception("The summary of a call of %s failed.", business.id)
            return []

        summaries = read_call_summaries(
            None if response.text is None else str(response.text), languages
        )
        if not summaries:
            LOGGER.warning("The model wrote no readable call summary.")

        return [
            CallSummary(language=language, text=text)
            for language, text in summaries.items()
        ]

    def _model_id(self) -> LlmModelId:
        return (
            self._app_settings.llm_summary_model_id or self._app_settings.llm_model_id
        )


def summary_languages(
    business: BusinessDocument,
    staff_languages: list[LanguageTag],
) -> list[LanguageTag]:
    """The owner's language, then the staff's, each once, at most four."""

    languages: list[LanguageTag] = []
    for language in [business.owner_language, *staff_languages]:
        if language not in languages:
            languages.append(language)

    return languages[:MAX_SUMMARY_LANGUAGES]


def pick_summary(
    summaries: list[CallSummary],
    language: LanguageTag,
) -> CallSummary | None:
    """The summary in the language, else in its base language, else none."""

    base: str = str(language).split("-")[0]
    for summary in summaries:
        if summary.language == language:
            return summary

    for summary in summaries:
        if str(summary.language).split("-")[0] == base:
            return summary

    return None
