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

# Words the concept's tax rule forbids on invoices, in English and Italian
# ("licenza", "consulenza", "consultazione").
FORBIDDEN_FRAGMENTS: tuple[str, ...] = ("licen", "consult", "consulen")

ENGLISH_SERVICE_PERIOD_LINE: str = (
    "Call and message handling service — Voice + chat, monthly, "
    "Oct 1, 2026 – Oct 31, 2026"
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


def test_invoice_line_names_the_service_and_the_plan() -> None:
    assert (
        describe_invoice(BillingTestbed(), invoice_input("en"))
        == ENGLISH_SERVICE_PERIOD_LINE
    )


def test_an_italian_owner_reads_the_english_invoice_until_the_draft_is_reviewed() -> (
    None
):
    # it.json is a draft (needs_review), and a draft never reaches an invoice:
    # issued invoices keep their wording, so Italian reads English for now.
    assert (
        describe_invoice(BillingTestbed(), invoice_input("it"))
        == ENGLISH_SERVICE_PERIOD_LINE
    )


@pytest.mark.parametrize("language", ["ru", "ka", "ru-KZ", "ar", "ja", "zh-Hant"])
def test_other_languages_read_the_english_invoice(language: str) -> None:
    # Russian and Georgian are no longer owner languages; the others never were.
    assert (
        describe_invoice(BillingTestbed(), invoice_input(language))
        == ENGLISH_SERVICE_PERIOD_LINE
    )


def test_setup_fee_line() -> None:
    assert (
        describe_invoice(
            BillingTestbed(),
            invoice_input("en", kind=InvoiceKind.SETUP_FEE),
        )
        == "Call and message handling service — setup"
    )


@pytest.mark.parametrize("language", ["en", "it", "ru"])
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
    testbed = BillingTestbed()

    english: str = describe_invoice(
        testbed, invoice_input("en", billing_period=BillingPeriod.ANNUAL)
    )
    italian: str = describe_invoice(
        testbed, invoice_input("it", billing_period=BillingPeriod.ANNUAL)
    )

    assert ", annual, " in english
    # A draft never reaches an invoice: the Italian owner reads the English line.
    assert italian == english
