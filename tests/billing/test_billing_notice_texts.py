"""Billing notice texts: payment failures, usage warnings and placeholders."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.schemas.constants.billing import BillingNoticeKind, PackageMetric
from app.schemas.dto.billing_ledger import BillingNotice
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import (
    IncludedDialogs,
    IncludedVoiceMinutes,
    PackageUsagePercent,
    UsedDialogs,
    UsedVoiceMinutes,
)
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.transformers.billing.billing_texts import fill_placeholders
from app.utilities.billing.billing_periods import to_microseconds
from tests.billing.billing_testbed import BillingTestbed, describe_notice
from tests.billing.billing_text_inputs import TBILISI, gel, tbilisi


def test_payment_failed_notice_names_amount_and_deadline_per_language() -> None:
    testbed = BillingTestbed()

    def render(language: str) -> str:
        return describe_notice(
            testbed,
            BillingNotice(
                kind=BillingNoticeKind.PAYMENT_FAILED,
                language=LanguageTag(language),
                timezone=TimezoneName(TBILISI),
                business_name=BusinessName("Funicular VR"),
                amount=gel(51700),
                deadline=tbilisi(2026, 11, 8, 9, 0),
            ),
        )

    assert render("en") == (
        "Funicular VR: the payment of GEL517.00 for the assistant did not go "
        "through. Please check the card and pay again in Billing. The assistant "
        "keeps full service until November 8, 2026; after that it will only take "
        "requests."
    )
    assert render("ru") == (
        "Funicular VR: оплата 517,00\xa0GEL за ассистента не прошла. Проверьте "
        "карту и оплатите снова в разделе «Тариф и счета». Ассистент работает в "
        "полном режиме до 8 ноября 2026 г., потом будет только принимать "
        "заявки."
    )
    assert render("ka") == (
        "Funicular VR: ასისტენტის გადახდა (517,00\xa0₾) ვერ შესრულდა. გთხოვთ, "
        "შეამოწმოთ ბარათი და ხელახლა გადაიხადოთ განყოფილებაში „ბილინგი“. "
        "ასისტენტი სრულ რეჟიმში იმუშავებს ამ თარიღამდე: 8 ნოემბერი, 2026; "
        "შემდეგ კი მხოლოდ მოთხოვნებს მიიღებს."
    )
    assert render("he") == (
        "Funicular VR: התשלום של \u200f517.00\xa0\u200fGEL עבור העוזר לא עבר. "
        "בדקו את הכרטיס ושלמו שוב ב„מסלול וחיוב”. העוזר ימשיך בשירות מלא עד "
        "8 בנובמבר 2026; אחר כך הוא רק יקבל פניות."
    )
    assert render("de") == (
        "Funicular VR: Die Zahlung von 517,00\xa0GEL für den Assistenten ist "
        "nicht durchgegangen. Bitte prüfen Sie die Karte und zahlen Sie erneut "
        "unter „Tarif und Abrechnung“. Der Assistent arbeitet bis zum 8. November "
        "2026 im vollen Betrieb; danach nimmt er nur noch Anfragen auf."
    )
    assert render("fr") == render("en")


def test_notice_dates_are_local_to_the_business() -> None:
    testbed = BillingTestbed()
    late_evening_utc = to_microseconds(
        datetime(2026, 11, 7, 23, 0, tzinfo=ZoneInfo("UTC"))
    )

    def render(timezone: str) -> str:
        return describe_notice(
            testbed,
            BillingNotice(
                kind=BillingNoticeKind.TRIAL_ENDED_UNPAID,
                language=LanguageTag("en"),
                timezone=TimezoneName(timezone),
                business_name=BusinessName("Café"),
                amount=gel(96000),
                deadline=late_evening_utc,
            ),
        )

    assert "November 8, 2026" in render("Asia/Tbilisi")
    assert "November 7, 2026" in render("America/New_York")


def test_notices_without_a_deadline_have_no_deadline_sentence() -> None:
    text: str = describe_notice(
        BillingTestbed(),
        BillingNotice(
            kind=BillingNoticeKind.LEADS_ONLY_STARTED,
            language=LanguageTag("ka"),
            timezone=TimezoneName(TBILISI),
            business_name=BusinessName("Funicular VR"),
            deadline=tbilisi(2026, 11, 8, 9, 0),
        ),
    )

    assert text == (
        "Funicular VR: გამოწერა გადაუხდელია, ამიტომ ასისტენტი ახლა მხოლოდ "
        "მოთხოვნებს იღებს და თქვენს გუნდს გადასცემს. სრული რეჟიმის აღსადგენად "
        "გადაიხადეთ განყოფილებაში „ბილინგი“."
    )


def test_usage_warnings_for_minutes_and_dialogs() -> None:
    testbed = BillingTestbed()
    minutes = BillingNotice(
        kind=BillingNoticeKind.PACKAGE_USAGE_WARNING,
        language=LanguageTag("ru"),
        timezone=TimezoneName(TBILISI),
        business_name=BusinessName("Funicular VR"),
        metric=PackageMetric.VOICE_MINUTES,
        usage_percent=PackageUsagePercent(82),
        used_voice_minutes=UsedVoiceMinutes(328),
        included_voice_minutes=IncludedVoiceMinutes(400),
        overage_price_per_minute=gel(44),
    )
    dialogs = BillingNotice(
        kind=BillingNoticeKind.PACKAGE_USAGE_WARNING,
        language=LanguageTag("en"),
        timezone=TimezoneName(TBILISI),
        business_name=BusinessName("Funicular VR"),
        metric=PackageMetric.DIALOGS,
        usage_percent=PackageUsagePercent(80),
        used_dialogs=UsedDialogs(1200),
        included_dialogs=IncludedDialogs(1500),
    )

    assert describe_notice(testbed, minutes) == (
        "Funicular VR: в этом периоде использовано 82% минут звонков из тарифа "
        "(328 из 400). Минуты сверх пакета стоят 0,44\xa0GEL за минуту."
    )
    assert describe_notice(testbed, dialogs) == (
        "Funicular VR: 80% of the dialogs in your plan are used this period "
        "(1,200 of 1,500). If they run short, choose a larger plan in Billing."
    )


def test_usage_warning_needs_its_metric() -> None:
    with pytest.raises(ValidationFailedError):
        describe_notice(
            BillingTestbed(),
            BillingNotice(
                kind=BillingNoticeKind.PACKAGE_USAGE_WARNING,
                language=LanguageTag("en"),
                timezone=TimezoneName(TBILISI),
                business_name=BusinessName("Funicular VR"),
            ),
        )


def test_placeholders_are_filled_once() -> None:
    assert (
        fill_placeholders(
            "{business}: {amount} {unknown}",
            {"business": "Bar {amount}", "amount": "5 GEL"},
        )
        == "Bar {amount}: 5 GEL {unknown}"
    )
