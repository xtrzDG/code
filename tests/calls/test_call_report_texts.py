"""The staff texts about a call, in English, Russian and Georgian."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.calls import (
    MissedCallReason,
    TextBackChannel,
    TextBackSkipReason,
    TextBackStatus,
)
from app.schemas.constants.conversations import CallOutcome
from app.schemas.dto.calls.call_summaries import CallReportTextInput, TextBackNote
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.contacts.strings import ContactName
from app.schemas.typings.conversations.constrained_integers import (
    CallDurationSeconds,
)
from app.schemas.typings.conversations.strings import UnverifiedReplyValue
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.transformers.notifications.call_report_brief_transformer import (
    CallReportBriefTransformer,
)
from app.transformers.notifications.call_report_text_transformer import (
    CallReportTextTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

# 2026-10-03 15:00 UTC (19:00 in Tbilisi).
STARTED_AT: Microseconds = Microseconds(1_791_039_600_000_000)


def facts(language: str = "en", **changes: object) -> CallReportTextInput:
    base = CallReportTextInput(
        business_name=BusinessName("Funicular VR"),
        language=LanguageTag(language),
        timezone=TimezoneName("Asia/Tbilisi"),
        started_at=STARTED_AT,
        caller_phone=FormattedPhoneNumber("+995 599 12 34 56"),
        duration_seconds=CallDurationSeconds(42),
        outcome=CallOutcome.LEAD,
    )
    return base.model_copy(update=changes)


@pytest.fixture
def detailed() -> CallReportTextTransformer:
    return CallReportTextTransformer(LocalizedTextResolver())


@pytest.fixture
def brief() -> CallReportBriefTransformer:
    return CallReportBriefTransformer(LocalizedTextResolver())


class TestSummaryText:
    def test_every_part_of_an_answered_call(
        self, detailed: CallReportTextTransformer
    ) -> None:
        text = detailed.transform(
            facts(
                caller_name=ContactName("Giorgi"),
                summary=CallSummaryText("Wants a banquet for 40 on Saturday."),
                unverified_values=[UnverifiedReplyValue("120 GEL")],
            )
        )

        assert str(text).split("\n") == [
            "Call summary · Funicular VR",
            "Caller: Giorgi (+995 599 12 34 56) · Oct 3, 2026, 7:00\u202fPM · 42 s",
            "Wants a banquet for 40 on Saturday.",
            "Result: request taken",
            "Please check: the assistant mentioned 120 GEL, which is not in your "
            "business data.",
        ]

    @pytest.mark.parametrize(
        ("language", "title", "result"),
        [
            ("ru", "Итог звонка · Funicular VR", "Итог: принята заявка"),
            ("ka", "ზარის შეჯამება · Funicular VR", "შედეგი: მოთხოვნა მიღებულია"),
            (
                "de",
                "Anrufzusammenfassung · Funicular VR",
                "Ergebnis: Anfrage aufgenommen",
            ),
            (
                "he",
                "סיכום שיחה · \u2068Funicular VR\u2069",
                "תוצאה: \u2068התקבלה פנייה\u2069",
            ),
            ("fr", "Call summary · Funicular VR", "Result: request taken"),
        ],
    )
    def test_in_the_recipients_language(
        self,
        detailed: CallReportTextTransformer,
        language: str,
        title: str,
        result: str,
    ) -> None:
        lines = str(detailed.transform(facts(language))).split("\n")

        assert lines[0] == title
        assert lines[2] == result

    def test_a_long_call_in_minutes(self, detailed: CallReportTextTransformer) -> None:
        text = detailed.transform(
            facts("ru", duration_seconds=CallDurationSeconds(185))
        )

        assert str(text).split("\n")[1].endswith(" · 3 мин 5 с")


class TestMissedCallText:
    def test_a_hidden_caller_who_got_an_sms(
        self, detailed: CallReportTextTransformer
    ) -> None:
        text = detailed.transform(
            facts(
                caller_phone=None,
                missed_reason=MissedCallReason.BUSY,
                text_back=TextBackNote(
                    status=TextBackStatus.QUEUED, channel=TextBackChannel.SMS
                ),
            )
        )

        lines = str(text).split("\n")
        assert lines[0] == "Missed call · Funicular VR"
        # No duration: the caller never talked to anyone.
        assert lines[1] == "Caller: hidden number · Oct 3, 2026, 7:00\u202fPM"
        assert lines[2] == "Why: the line was busy"
        assert lines[3] == (
            "We sent the caller an SMS. Please call them back if you can."
        )

    @pytest.mark.parametrize(
        ("note", "why"),
        [
            (
                TextBackNote(
                    status=TextBackStatus.SKIPPED,
                    skip_reason=TextBackSkipReason.OPTED_OUT,
                ),
                "клиент просил не присылать сообщения",
            ),
            (
                TextBackNote(status=TextBackStatus.FAILED),
                "сообщение не удалось отправить",
            ),
        ],
    )
    def test_why_the_caller_was_not_written_to(
        self,
        detailed: CallReportTextTransformer,
        note: TextBackNote,
        why: str,
    ) -> None:
        text = detailed.transform(
            facts("ru", missed_reason=MissedCallReason.NO_ANSWER, text_back=note)
        )

        assert str(text).split("\n")[-1] == (
            f"Звонившему мы не написали ({why}). Перезвоните, если можете."
        )

    def test_georgian(self, detailed: CallReportTextTransformer) -> None:
        text = detailed.transform(
            facts(
                "ka",
                missed_reason=MissedCallReason.TRANSFER_UNANSWERED,
                text_back=TextBackNote(
                    status=TextBackStatus.SENT, channel=TextBackChannel.WHATSAPP
                ),
            )
        )

        lines = str(text).split("\n")
        assert lines[0] == "გამოტოვებული ზარი · Funicular VR"
        assert lines[-1] == (
            "დამრეკს WhatsApp-ში მივწერეთ — მისი პასუხი შემოსულებში მოვა."
        )


class TestBrief:
    def test_an_answered_call(self, brief: CallReportBriefTransformer) -> None:
        result = brief.transform(facts("ru"))

        assert str(result.title) == "Итог звонка · Funicular VR"
        assert str(result.detail) == "принята заявка · 42 с"

    def test_a_missed_call_says_why_and_nothing_about_the_caller(
        self, brief: CallReportBriefTransformer
    ) -> None:
        result = brief.transform(facts(missed_reason=MissedCallReason.NOT_STARTED))

        assert str(result.title) == "Missed call · Funicular VR"
        assert str(result.detail) == "the assistant could not take the call"
        assert "599" not in str(result.title) + str(result.detail)

    def test_without_an_outcome_there_is_no_detail(
        self, brief: CallReportBriefTransformer
    ) -> None:
        assert brief.transform(facts(outcome=None)).detail is None
