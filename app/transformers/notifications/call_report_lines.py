"""The parts of a staff text about a call that the detailed and brief texts share."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.constants.calls import TextBackChannel, TextBackStatus
from app.schemas.dto.calls.call_summaries import CallReportTextInput, TextBackNote
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.notifications.call_report_texts import (
    CALL_SUMMARY_TITLE,
    MINUTES_AND_SECONDS,
    MISSED_CALL_TITLE,
    NOT_TEXTED,
    SECONDS_ONLY,
    SKIP_REASON_LABELS,
    TEXT_BACK_FAILED,
    TEXTED_BY_SMS,
    TEXTED_BY_WHATSAPP,
)
from app.transformers.notifications.message_rendering import render, resolve_label
from app.utilities.scheduling.localized_formatting import choose_template_language

SECONDS_PER_MINUTE: int = 60
TEXTED_LINES: dict[TextBackChannel, LocalizedText] = {
    TextBackChannel.WHATSAPP: TEXTED_BY_WHATSAPP,
    TextBackChannel.SMS: TEXTED_BY_SMS,
}


def report_title(input_data: CallReportTextInput) -> LocalizedText:
    """A caller who did not get through gets the missed-call title."""

    return CALL_SUMMARY_TITLE if input_data.missed_reason is None else MISSED_CALL_TITLE


def report_language(input_data: CallReportTextInput) -> LanguageTag:
    """The language every part of the text is rendered in."""

    return choose_template_language(report_title(input_data), input_data.language)


def describe_duration(
    resolver: LocalizedTextResolverContract,
    duration_seconds: int,
    language: LanguageTag,
) -> str:
    minutes, seconds = divmod(max(duration_seconds, 0), SECONDS_PER_MINUTE)
    if minutes == 0:
        return render(resolver, SECONDS_ONLY, language, {"seconds": str(seconds)})

    return render(
        resolver,
        MINUTES_AND_SECONDS,
        language,
        {"minutes": str(minutes), "seconds": str(seconds)},
    )


def describe_text_back(
    resolver: LocalizedTextResolverContract,
    note: TextBackNote,
    language: LanguageTag,
) -> str:
    """The caller was written to (and how), or why not."""

    if (
        note.status in {TextBackStatus.QUEUED, TextBackStatus.SENT}
        and note.channel is not None
    ):
        return render(resolver, TEXTED_LINES[note.channel], language, {})

    why: str = (
        str(resolver.resolve(TEXT_BACK_FAILED, language))
        if note.skip_reason is None
        else resolve_label(resolver, SKIP_REASON_LABELS, note.skip_reason, language)
    )
    return render(resolver, NOT_TEXTED, language, {"why": why})
