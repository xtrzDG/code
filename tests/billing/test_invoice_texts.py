"""Invoice line texts: service and plan names per language, never a license."""

import pytest

from app.registries.billing.plan_registry import PlanRegistry
from app.schemas.constants.billing import BillingPeriod, InvoiceKind, PlanKey
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from tests.billing.billing_testbed import BillingTestbed, describe_invoice
from tests.billing.billing_text_inputs import TBILISI, tbilisi

# Words the concept's tax rule forbids on invoices, in every language.
FORBIDDEN_FRAGMENTS: tuple[str, ...] = (
    "licen",
    "consult",
    "лиценз",
    "консульт",
    "ლიცენზ",
    "კონსულტ",
)


def invoice_input(
    language: str,
    kind: InvoiceKind = InvoiceKind.SERVICE_PERIOD,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
    plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
) -> InvoiceDescriptionInput:
    return InvoiceDescriptionInput(
        kind=kind,
        language=LanguageTag(language),
        timezone=TimezoneName(TBILISI),
        plan_names=PlanRegistry().get(plan_key).names,
        billing_period=billing_period,
        period_start=tbilisi(2026, 10, 1, 0, 0),
        period_end=tbilisi(2026, 11, 1, 0, 0),
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (
            "en",
            "Call and message handling service — Voice + chat, monthly, "
            "Oct 1, 2026 – Oct 31, 2026",
        ),
        (
            "ru",
            "Услуга приёма и обработки обращений — Голос + чат, помесячно, "
            "1 окт. 2026 г. – 31 окт. 2026 г.",
        ),
        (
            "ka",
            "ზარებისა და შეტყობინებების მიღებისა და დამუშავების მომსახურება — "
            "ხმა + ჩატი, ყოველთვიური, 1 ოქტ. 2026 – 31 ოქტ. 2026",
        ),
        (
            "ru-KZ",
            "Услуга приёма и обработки обращений — Голос + чат, помесячно, "
            "1 окт. 2026 г. – 31 окт. 2026 г.",
        ),
    ],
)
def test_invoice_line_names_the_service_in_the_owner_language(
    language: str,
    expected: str,
) -> None:
    assert describe_invoice(BillingTestbed(), invoice_input(language)) == expected


@pytest.mark.parametrize("language", ["he", "ar", "ja", "it", "zh-Hant"])
def test_other_languages_read_the_english_invoice(language: str) -> None:
    testbed = BillingTestbed()

    assert describe_invoice(testbed, invoice_input(language)) == describe_invoice(
        testbed, invoice_input("en")
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Call and message handling service — setup"),
        ("ru", "Услуга приёма и обработки обращений — подключение"),
        (
            "ka",
            "ზარებისა და შეტყობინებების მიღებისა და დამუშავების მომსახურება — ჩართვა",
        ),
    ],
)
def test_setup_fee_line(language: str, expected: str) -> None:
    assert (
        describe_invoice(
            BillingTestbed(),
            invoice_input(language, kind=InvoiceKind.SETUP_FEE),
        )
        == expected
    )


@pytest.mark.parametrize("language", ["en", "ru", "ka", "he", "ar"])
@pytest.mark.parametrize("kind", list(InvoiceKind))
@pytest.mark.parametrize("billing_period", list(BillingPeriod))
@pytest.mark.parametrize("plan_key", list(PlanKey))
def test_invoices_never_mention_a_license_or_a_consultation(
    language: str,
    kind: InvoiceKind,
    billing_period: BillingPeriod,
    plan_key: PlanKey,
) -> None:
    line: str = describe_invoice(
        BillingTestbed(),
        invoice_input(language, kind, billing_period, plan_key),
    ).casefold()

    assert not any(fragment in line for fragment in FORBIDDEN_FRAGMENTS)


def test_annual_invoice_line_says_annual() -> None:
    line: str = describe_invoice(
        BillingTestbed(),
        invoice_input("ru", billing_period=BillingPeriod.ANNUAL),
    )

    assert "за год" in line
