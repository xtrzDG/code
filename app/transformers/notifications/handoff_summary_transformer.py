from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.handoffs import CodedHandoffSummary, HandoffSummaryInput
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.handoffs.strings import HandoffSummary
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.handoff_summary_texts import (
    QUOTED_CUSTOMER_MESSAGE,
    QUOTED_REPLY,
    SUMMARY_TEXTS,
    SUMMARY_TEXTS_WITH_VALUES,
    VALUE_SEPARATOR,
)
from app.transformers.notifications.message_rendering import render
from app.utilities.scheduling.localized_formatting import choose_template_language


class HandoffSummaryTransformer(
    TransformerContract[HandoffSummaryInput, HandoffSummary]
):
    """
    The summary of a handoff the platform created, in one reader's
    language: what happened (with the flagged values when there are any),
    then the quoted words, e.g. "Помощник был временно недоступен и не
    смог ответить. Сообщение клиента: «Можно с собакой?»". Quoted words and
    values stay as they were written.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: HandoffSummaryInput) -> HandoffSummary:
        summary: CodedHandoffSummary = input_data.summary
        event: LocalizedText = SUMMARY_TEXTS[summary.code]
        values: str = VALUE_SEPARATOR.join(
            str(value) for value in summary.flagged_values
        )
        with_values: LocalizedText | None = SUMMARY_TEXTS_WITH_VALUES.get(summary.code)
        if values and with_values is not None:
            event = with_values

        language: LanguageTag = choose_template_language(event, input_data.language)
        parts: list[str] = [
            render(self._text_resolver, event, language, {"values": values})
        ]
        if summary.quoted_text is not None:
            quote: LocalizedText = (
                QUOTED_REPLY
                if summary.code is HandoffSummaryCode.REPLY_UNDELIVERED
                else QUOTED_CUSTOMER_MESSAGE
            )
            parts.append(
                render(
                    self._text_resolver,
                    quote,
                    language,
                    {"text": str(summary.quoted_text)},
                )
            )

        return HandoffSummary(" ".join(parts))
