"""The digest and monthly report as owners read them, in en, ru and ka."""

import json

from app.schemas.dto.value.value_digests import ValueDigestText, ValueDigestTextInput
from app.schemas.dto.value.value_reports import ValueReportView
from app.transformers.notifications.value_digest_text_transformer import (
    ValueDigestTextTransformer,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver

LINK: str = "https://cabinet.example.com/n/" + "A" * 67
TOTALS: dict[str, int | None] = {
    "conversation_count": 134,
    "after_hours_conversation_count": 18,
    "customer_message_count": 420,
    "assistant_reply_count": 380,
    "call_count": 12,
    "booking_count": 25,
    "assistant_booking_count": 22,
    "request_count": 6,
    "handoff_count": 3,
    "staff_minutes_saved": 523,
    "estimated_revenue_minor": 264_000,
}


def report(**changes: object) -> ValueReportView:
    data: dict[str, object] = {
        "id": "value_report_8d3c5f27-a196-5e0b-8c74-5e2b9a1d6f03",
        "business_id": "business_8d3c5f27-a196-4e0b-8c74-5e2b9a1d6f03",
        "kind": "weekly",
        "period_key": "2026-W39",
        "date_from": "2026-09-21",
        "date_to": "2026-09-27",
        "previous_date_from": "2026-09-14",
        "previous_date_to": "2026-09-20",
        "currency_code": "GEL",
        "value_basis": "bookings",
        "average_check_minor": 12_000,
        "average_check_source": "owner",
        "current": TOTALS,
        "previous": {**TOTALS, "assistant_booking_count": 19},
        "delivery": "sent",
        "recipient_count": 1,
        "created_at": 1,
        **changes,
    }
    return ValueReportView.model_validate_json(json.dumps(data))


def digest(
    language: str, view: ValueReportView, link: str | None = LINK
) -> ValueDigestText:
    return ValueDigestTextTransformer(LocalizedTextResolver()).transform(
        ValueDigestTextInput.model_validate_json(
            json.dumps(
                {
                    "business_name": "Café Rustaveli",
                    "language": language,
                    "report": json.loads(view.model_dump_json()),
                    "link": link,
                }
            )
        )
    )


def test_the_weekly_digest_in_english() -> None:
    text = digest("en", report())

    assert str(text.message).split("\n") == [
        "Your assistant last week · Café Rustaveli",
        "Sep 21\u2009–\u200927",
        "Bookings by the assistant: 22 ≈ GEL2,640 (▲ 16% vs the week before)",
        "Conversations after hours: 18 (of 134)",
        "Staff time saved: about 9 h",
        "Conversations: 134 · Requests: 6 · Needed a person: 3",
        f"Open the report: {LINK}",
        "You get this summary as an owner of Café Rustaveli. To stop it, open "
        "the report and turn it off under “Your summaries”.",
    ]
    assert str(text.brief.title) == "Your assistant last week · Café Rustaveli"
    assert str(text.brief.detail) == (
        "Bookings by the assistant: 22 ≈ GEL2,640 · Staff time saved: about 9 h"
    )


def test_the_monthly_report_in_russian_and_georgian() -> None:
    monthly = report(
        kind="monthly",
        period_key="2026-09",
        date_from="2026-09-01",
        date_to="2026-09-30",
        average_check_source="niche_default",
    )

    russian = str(digest("ru", monthly).message).split("\n")
    georgian = str(digest("ka", monthly).message).split("\n")

    assert russian[0] == "Отчёт за месяц: сентябрь 2026\u202fг. · Café Rustaveli"
    assert russian[1] == (
        "Брони через помощника: 22 ≈ 2\xa0640\xa0GEL (▲ 16% к предыдущему месяцу)"
    )
    assert (
        "Сумма посчитана по типичному чеку 120\xa0GEL; укажите свой в кабинете."
        in russian
    )
    assert georgian[0] == "თვის ანგარიში: სექტემბერი, 2026 · Café Rustaveli"
    assert georgian[1].startswith("ასისტენტის ჯავშნები: 22 ≈ 2\xa0640\xa0₾")
    assert "საუბრები არასამუშაო საათებში: 18 (134-დან)" in georgian


def test_without_a_check_or_a_link_the_counts_stay_and_a_hint_follows() -> None:
    quiet_money = report(
        average_check_minor=None,
        average_check_source="none",
        current={**TOTALS, "estimated_revenue_minor": None, "staff_minutes_saved": 40},
        previous={**TOTALS, "assistant_booking_count": 0},
    )

    lines = str(digest("en", quiet_money, link=None).message).split("\n")

    assert lines[2] == "Bookings by the assistant: 22"
    assert lines[4] == "Staff time saved: about 40 min"
    assert "Add your average check in the cabinet to see this in money." in lines
    assert not any("Open the report" in line for line in lines)


def test_a_shop_counts_its_orders_and_a_fall_shows_down() -> None:
    shop = report(
        kind="daily",
        period_key="2026-09-27",
        date_from="2026-09-27",
        date_to="2026-09-27",
        value_basis="requests",
        previous={**TOTALS, "request_count": 8},
    )

    lines = str(digest("en", shop).message).split("\n")

    assert lines[0] == "Your assistant yesterday · Café Rustaveli"
    assert lines[1] == "September 27, 2026"
    assert lines[2] == (
        "Orders and requests taken: 6 ≈ GEL2,640 (▼ 25% vs the day before)"
    )
    assert lines[5] == "Conversations: 134 · Needed a person: 3"


def test_an_unknown_language_reads_english() -> None:
    assert str(digest("tr", report()).message).startswith("Your assistant last week")
