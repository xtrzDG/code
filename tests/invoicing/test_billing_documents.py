"""
The invoice and receipt pages: in the reader's language, with the number,
both parties, the VAT and how it was paid; every value escaped; an invoice
from before numbering numbered once, at its first download; each download
audited.
"""

import pytest

from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.invoicing import BillingDocumentKind, TaxTreatment
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.invoicing import BillingDocumentFile, BillingDocumentQuery
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.billing_settings import ITALY
from tests.billing.paid_world import PaidWorld, checkout, payment_order
from tests.invoicing.document_world import (
    DocumentWorld,
    HtmlEchoRenderer,
    build_document_world,
)
from tests.invoicing.invoicing_world import build_seller_trial, save_billing_profile


def documents_of(world: PaidWorld) -> DocumentWorld:
    return build_document_world(world, HtmlEchoRenderer())


def first_invoice(world: PaidWorld) -> InvoiceDocument:
    return world.testbed.invoices(world.business.id)[0]


def download(
    documents: DocumentWorld,
    invoice: InvoiceDocument,
    kind: BillingDocumentKind = BillingDocumentKind.INVOICE,
    language: str = "ru",
) -> tuple[BillingDocumentFile, str]:
    world = documents.world
    document = documents.get_document.run(
        BillingDocumentQuery(
            user_id=world.owner.id,
            business_id=world.business.id,
            invoice_id=invoice.id,
            kind=kind,
            display_language=LanguageTag(language),
        )
    )
    return document, document.content.decode()


def pay(world: PaidWorld) -> None:
    session = checkout(world)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            payment_order(world, session),
            "approved",
            masked_card="444455XXXXXX1111",
            card_type="VISA",
        )
    )


def test_the_russian_invoice_names_the_number_both_parties_and_the_vat() -> None:
    world = build_seller_trial(is_vat_registered=True)
    save_billing_profile(world, "GE", tax_id="405123456")
    checkout(world)
    documents = documents_of(world)

    document, page = download(documents, first_invoice(world))

    assert str(document.file_name) == "invoice-AW-2026-000001.pdf"
    for text in (
        "<h1>Счёт</h1>",
        "№ AW-2026-000001",
        "Ожидает оплаты",
        "Исполнитель",
        "Assistant Workshop LLC",
        "Налоговый номер: 405999999",
        "Заказчик",
        "Mtsvane Ezo LLC",
        "Налоговый номер: 405123456",
        "Грузия",
        "Итого без НДС",
        "НДС 18\u00a0%",
        "93,06",
        "Итого к оплате",
        "610,06",
        "Оплатите онлайн в кабинете: Настройки → Тариф и оплата.",
        "НДС начислен по ставке 18\u00a0%.",
        "Документ сформирован электронно: Assistant Workshop LLC.",
    ):
        assert text in page, text


def test_a_receipt_comes_with_the_payment() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    documents = documents_of(world)

    with pytest.raises(ConflictError, match="not paid"):
        download(documents, first_invoice(world), BillingDocumentKind.RECEIPT)

    pay(world)
    receipt, page = download(
        documents, first_invoice(world), BillingDocumentKind.RECEIPT, "ka"
    )

    assert str(receipt.file_name) == "receipt-AW-2026-000001.pdf"
    for text in (
        "გადახდის ქვითარი",
        "ინვოისი № AW-2026-000001",
        "გადახდის თარიღი",
        "ბარათი VISA, ბოლო ციფრები 1111",
        "მიღებული თანხა",
        "დღგ არ ერიცხება",
    ):
        assert text in page, text
    assert "ჯამი დღგ-ის გარეშე" not in page


def test_a_paid_invoice_in_english_says_when_and_how_it_was_paid() -> None:
    world = build_seller_trial(is_vat_registered=False)
    pay(world)

    _, page = download(documents_of(world), first_invoice(world), language="en")

    for text in (
        "<h1>Invoice</h1>",
        "Paid",
        "Payment date",
        "VISA card ending in 1111",
    ):
        assert text in page, text
    assert "Total paid" in page
    assert "Pay online" not in page


def test_other_languages_read_english_with_english_dates() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)

    _, page = download(documents_of(world), first_invoice(world), language="de")

    assert '<html lang="en">' in page
    assert "Seller" in page and "Verkäufer" not in page


def test_buyers_abroad_read_why_there_is_no_vat() -> None:
    business = build_seller_trial(is_vat_registered=True, country=ITALY)
    save_billing_profile(business, "IT", tax_id="IT12345678901")
    consumer = build_seller_trial(is_vat_registered=True, country=ITALY)
    checkout(business)
    checkout(consumer)

    _, reverse = download(
        documents_of(business), first_invoice(business), language="en"
    )
    _, outside = download(
        documents_of(consumer), first_invoice(consumer), language="en"
    )

    assert "Reverse charge: VAT is to be accounted for by the recipient." in reverse
    assert "Not subject to VAT in Georgia" in outside
    assert "VAT 18%" not in reverse + outside


def test_every_value_on_the_page_is_escaped() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    invoice = first_invoice(world)
    invoice.description = InvoiceDescription('<img src="x" onerror="alert(1)">')
    world.testbed.invoice_repo.save(invoice)

    _, page = download(documents_of(world), invoice, language="en")

    assert "<img" not in page
    assert "&lt;img src=&quot;x&quot; onerror=&quot;alert(1)&quot;&gt;" in page


def test_an_invoice_from_before_numbering_gets_its_number_once() -> None:
    world = build_seller_trial(is_vat_registered=True)
    testbed = world.testbed
    legacy = InvoiceDocument(
        business_id=world.business.id,
        kind=InvoiceKind.SERVICE_PERIOD,
        description=InvoiceDescription("Call and message handling service"),
        amount_minor=MoneyAmountMinor(51_700),
        currency_code=world.business.currency_code,
        status=InvoiceStatus.PAID,
        period_start=testbed.clock.now(),
        period_end=testbed.clock.now(),
        created_at=testbed.clock.now(),
        updated_at=testbed.clock.now(),
    )
    testbed.invoice_repo.save(legacy)
    documents = documents_of(world)

    first, _ = download(documents, legacy)
    again, _ = download(documents, legacy, BillingDocumentKind.RECEIPT)

    stored = testbed.invoice_repo.get(world.business.id, legacy.id)
    assert stored is not None
    assert str(stored.number) == "AW-2026-000001"
    assert str(first.file_name) == "invoice-AW-2026-000001.pdf"
    assert str(again.file_name) == "receipt-AW-2026-000001.pdf"
    # Charged before VAT existed: the amount stays, without VAT.
    assert int(stored.amount_minor) == 51_700
    assert stored.tax_treatment is TaxTreatment.NOT_REGISTERED
    assert int(stored.tax_minor or 0) == 0


def test_a_voided_invoice_from_before_numbering_has_no_document() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    invoice = first_invoice(world)
    invoice.number = None
    invoice.status = InvoiceStatus.VOID
    world.testbed.invoice_repo.save(invoice)

    with pytest.raises(ConflictError, match="cancelled"):
        download(documents_of(world), invoice)


def test_each_download_is_audited_as_an_export() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)

    download(documents_of(world), first_invoice(world))

    entries = [
        entry
        for entry in world.testbed.audit_log_repo.list_by_business(world.business.id)
        if str(entry.entity) == "billing_document"
    ]
    assert len(entries) == 1
    assert entries[0].action is AuditAction.EXPORT
    assert entries[0].actor_id == world.owner.id
    assert str(entries[0].entity_id) == "invoice-AW-2026-000001.pdf"
