from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.calls.call_summaries import CallReportTextInput
from app.schemas.dto.notifications.staff_alerts import StaffAlertBrief
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.notifications.strings import (
    StaffAlertDetail,
    StaffAlertTitle,
)
from app.transformers.notifications.call_report_lines import (
    describe_duration,
    report_language,
    report_title,
)
from app.transformers.notifications.call_report_texts import (
    BRIEF_DETAIL,
    CALL_OUTCOME_LABELS,
    MISSED_REASON_LABELS,
)
from app.transformers.notifications.message_rendering import render, resolve_label


class CallReportBriefTransformer(
    TransformerContract[CallReportTextInput, StaffAlertBrief]
):
    """
    The brief of a call for a locked screen, an SMS or an e-mail subject:
    "Call summary · <business>" with how it ended and how long it took, or
    "Missed call · <business>" with why. Nothing about the caller: their
    number, name and the summary stay behind the link.
    """

    def __init__(self, text_resolver: LocalizedTextResolverContract) -> None:
        self._text_resolver: LocalizedTextResolverContract = text_resolver

    def transform(self, input_data: CallReportTextInput) -> StaffAlertBrief:
        language: LanguageTag = report_language(input_data)
        title = StaffAlertTitle(
            render(
                self._text_resolver,
                report_title(input_data),
                language,
                {"business": str(input_data.business_name)},
            )
        )
        return StaffAlertBrief(title=title, detail=self._detail(input_data, language))

    def _detail(
        self,
        input_data: CallReportTextInput,
        language: LanguageTag,
    ) -> StaffAlertDetail | None:
        if input_data.missed_reason is not None:
            return StaffAlertDetail(
                resolve_label(
                    self._text_resolver,
                    MISSED_REASON_LABELS,
                    input_data.missed_reason,
                    language,
                )
            )

        if input_data.outcome is None or input_data.duration_seconds is None:
            return None

        return StaffAlertDetail(
            render(
                self._text_resolver,
                BRIEF_DETAIL,
                language,
                {
                    "outcome": resolve_label(
                        self._text_resolver,
                        CALL_OUTCOME_LABELS,
                        input_data.outcome,
                        language,
                    ),
                    "duration": describe_duration(
                        self._text_resolver,
                        int(input_data.duration_seconds),
                        language,
                    ),
                },
            )
        )
