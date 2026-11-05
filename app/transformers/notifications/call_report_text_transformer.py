from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.calls.call_summaries import CallReportTextInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.call_report_lines import (
    describe_duration,
    describe_text_back,
    report_language,
    report_title,
)
from app.transformers.notifications.call_report_texts import (
    BOOKING_LINE,
    CALL_OUTCOME_LABELS,
    CALLER_LINE,
    HIDDEN_NUMBER,
    MISSED_REASON_LABELS,
    REASON_LINE,
    RESULT_LINE,
    UNVERIFIED_LINE,
)
from app.transformers.notifications.message_rendering import render, resolve_label
from app.utilities.channels.local_moments import format_local_moment

MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_LISTED_VALUES: int = 10
VALUE_SEPARATOR: str = ", "


class CallReportTextTransformer(TransformerContract[CallReportTextInput, MessageText]):
    """
    The staff text about a call for chats staff linked themselves
    (Telegram, WhatsApp): the title, who called and when (and for how
    long), the summary, how the call ended with the booking it made, the
    values the phone assistant said that the business data does not back;
    for a caller who did not get through, why, and whether we wrote to
    them. Every line is in the recipient's language (the summary is the
    one written in it).
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: CallReportTextInput) -> MessageText:
        language: LanguageTag = report_language(input_data)
        resolver: LocalizedTextResolverContract = self._text_resolver
        lines: list[str] = [
            render(
                resolver,
                report_title(input_data),
                language,
                {"business": str(input_data.business_name)},
            ),
            render(
                resolver,
                CALLER_LINE,
                language,
                {
                    "caller": self._caller(input_data, language),
                    "when": self._when(input_data, language),
                },
            ),
        ]
        if input_data.summary is not None:
            lines.append(str(input_data.summary))

        if input_data.missed_reason is not None:
            reason: str = resolve_label(
                resolver, MISSED_REASON_LABELS, input_data.missed_reason, language
            )
            lines.append(render(resolver, REASON_LINE, language, {"reason": reason}))
        elif input_data.outcome is not None:
            outcome: str = resolve_label(
                resolver, CALL_OUTCOME_LABELS, input_data.outcome, language
            )
            lines.append(render(resolver, RESULT_LINE, language, {"outcome": outcome}))

        if input_data.booking is not None:
            lines.append(
                render(
                    resolver,
                    BOOKING_LINE,
                    language,
                    {
                        "when": format_local_moment(
                            int(input_data.booking.starts_at),
                            input_data.timezone,
                            language,
                        ),
                        "party": str(int(input_data.booking.party_size)),
                    },
                )
            )

        if input_data.unverified_values:
            values: str = VALUE_SEPARATOR.join(
                str(value) for value in input_data.unverified_values[:MAX_LISTED_VALUES]
            )
            lines.append(
                render(resolver, UNVERIFIED_LINE, language, {"values": values})
            )

        if input_data.text_back is not None:
            lines.append(describe_text_back(resolver, input_data.text_back, language))

        return MessageText("\n".join(lines))

    def _caller(self, input_data: CallReportTextInput, language: LanguageTag) -> str:
        phone: str = (
            str(self._text_resolver.resolve(HIDDEN_NUMBER, language))
            if input_data.caller_phone is None
            else str(input_data.caller_phone)
        )
        if input_data.caller_name is None:
            return phone

        return f"{input_data.caller_name} ({phone})"

    def _when(self, input_data: CallReportTextInput, language: LanguageTag) -> str:
        moment: str = format_local_moment(
            int(input_data.started_at) // MICROSECONDS_PER_SECOND,
            input_data.timezone,
            language,
        )
        if input_data.duration_seconds is None or input_data.missed_reason is not None:
            return moment

        duration: str = describe_duration(
            self._text_resolver, int(input_data.duration_seconds), language
        )
        return f"{moment} · {duration}"
