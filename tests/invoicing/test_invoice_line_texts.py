"""
The invoice line in the languages of the PDFs: worded once at issue in
English, Russian and Georgian without its dates, printed in the page's
language (never another one), shown in the cabinet's language, and the
issued line for an invoice from before the PDFs.
"""

import pytest
from typed_time_provider import Microseconds

from app.registries.billing.plan_catalog import PLAN_DEFINITIONS
from app.registries.demo.berlin_salon.salon_activity import SALON_INVOICE_LINES
from app.schemas.constants.billing import BillingPeriod, InvoiceKind, PlanKey
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.domain.billing_profiles import InvoiceLineText
from app.schemas.dto.billing_cabinet import BillingOverviewQuery
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.typings.billing.constrained_integers import (
    MoneyAmountMinor,
    OverageVoiceMinutes,
)
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.transformers.invoicing.invoice_line_texts_transformer import (
    InvoiceLineTextsTransformer,
)
from app.utilities.billing.invoice_lines import word_invoice_line
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.billing.paid_world import checkout
from tests.invoicing.document_world import HtmlEchoRenderer, build_document_world
from tests.invoicing.invoicing_world import build_seller_trial

START: Microseconds = Microseconds(1_790_845_200_000_000)
PLANS = {plan.key: plan for plan in PLAN_DEFINITIONS}


def line_input(
    kind: InvoiceKind,
    plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
    billing_period: BillingPeriod = BillingPeriod.MONTHLY,
    minutes: int | None = None,
) -> InvoiceDescriptionInput:
    return InvoiceDescriptionInput(
        kind=kind,
        language=LanguageTag("ka"),
        timezone=TimezoneName("Asia/Tbilisi"),
        plan_names=PLANS[plan_key].names,
        billing_period=billing_period,
        period_start=START,
        period_end=START,
        overage_voice_minutes=None if minutes is None else OverageVoiceMinutes(minutes),
    )


def word(description_input: InvoiceDescriptionInput) -> dict[str, str]:
    lines = InvoiceLineTextsTransformer(LocalizedTextResolver()).transform(
        description_input
    )
    return {str(line.language): str(line.text) for line in lines}


def test_a_service_period_names_the_plan_and_its_billing_period_without_dates() -> None:
    assert word(line_input(InvoiceKind.SERVICE_PERIOD)) == {
        "en": "Call and message handling service — Voice + chat, monthly",
        "ru": "Услуга приёма и обработки обращений — Голос + чат, помесячно",
        "ka": "ზარებისა და შეტყობინებების მიღებისა და დამუშავების მომსახურება — "
        "ხმა + ჩატი, ყოველთვიური",
    }


@pytest.mark.parametrize(
    ("kind", "minutes", "english", "russian"),
    [
        (
            InvoiceKind.SETUP_FEE,
            None,
            "Call and message handling service — setup",
            "Услуга приёма и обработки обращений — подключение",
        ),
        (
            InvoiceKind.USAGE_OVERAGE,
            1234,
            "Call and message handling service — 1,234 call minutes above the package",
            "Услуга приёма и обработки обращений — 1\xa0234 мин. звонков сверх пакета",
        ),
    ],
)
def test_the_setup_fee_and_the_overage_lines(
    kind: InvoiceKind, minutes: int | None, english: str, russian: str
) -> None:
    worded = word(line_input(kind, minutes=minutes))

    assert (worded["en"], worded["ru"]) == (english, russian)
    assert set(worded) == {"en", "ru", "ka"}


def test_the_demo_salon_invoice_reads_as_the_platform_words_it() -> None:
    worded = word(line_input(InvoiceKind.SERVICE_PERIOD, PlanKey.CHAT))

    assert worded == SALON_INVOICE_LINES


def test_a_reader_gets_the_line_in_their_language_or_the_issued_one() -> None:
    invoice = InvoiceDocument(
        business_id=BusinessId(),
        description=InvoiceDescription("Услуга — Чат, помесячно, 1–31 окт."),
        amount_minor=MoneyAmountMinor(9_900),
        currency_code=CurrencyCode("EUR"),
        period_start=START,
        period_end=START,
        line_texts=[
            InvoiceLineText(
                language=LanguageTag("en"), text=InvoiceDescription("Service — Chat")
            ),
            InvoiceLineText(
                language=LanguageTag("ka"), text=InvoiceDescription("მომსახურება")
            ),
        ],
    )

    assert str(word_invoice_line(invoice, LanguageTag("en-GB"))) == "Service — Chat"
    assert str(word_invoice_line(invoice, LanguageTag("ka"))) == "მომსახურება"
    # No Russian wording: the line as issued (an invoice from before the PDFs).
    assert str(word_invoice_line(invoice, LanguageTag("ru"))) == (
        "Услуга — Чат, помесячно, 1–31 окт."
    )


def test_an_issued_invoice_prints_and_shows_its_line_in_the_readers_language() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    invoice = world.testbed.invoices(world.business.id)[0]
    documents = build_document_world(world, HtmlEchoRenderer()).documents

    russian_page = documents.produce(
        world.business, invoice, BillingDocumentKind.INVOICE, LanguageTag("ru")
    ).content.decode()
    overview = world.testbed.get_overview.run(
        BillingOverviewQuery(
            user_id=world.owner.id,
            business_id=world.business.id,
            display_language=LanguageTag("en"),
        )
    )

    assert str(world.business.owner_language) == "ka"
    assert "Услуга приёма и обработки обращений — Голос + чат, помесячно" in (
        russian_page
    )
    assert "მომსახურება" not in russian_page
    assert str(overview.invoices[0].description) == (
        "Call and message handling service — Voice + chat, monthly"
    )
    # The issued line in the owner language keeps its dates.
    assert str(invoice.description) != str(overview.invoices[0].description)
