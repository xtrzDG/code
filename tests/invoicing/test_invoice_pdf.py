"""
PDF smoke test: WeasyPrint lays the invoice and the receipt out in
Georgian, Russian and English, and fetches nothing the page names.
"""

import urllib.request
from typing import Any

import pytest

from app.adapters.documents.weasyprint_invoice_document_renderer_adapter import (
    WeasyPrintInvoiceDocumentRendererAdapter,
)
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.invoicing.strings import BillingDocumentHtml
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.billing.paid_world import checkout, payment_order
from tests.invoicing.document_world import build_document_world
from tests.invoicing.invoicing_world import build_seller_trial, save_billing_profile

MIN_PDF_BYTES: int = 3_000


@pytest.mark.parametrize("language", ["ka", "ru", "en"])
def test_the_invoice_and_its_receipt_render_as_pdf(language: str) -> None:
    world = build_seller_trial(is_vat_registered=True)
    save_billing_profile(world, "GE", tax_id="405123456")
    session = checkout(world)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(
            payment_order(world, session),
            "approved",
            masked_card="444455XXXXXX1111",
            card_type="VISA",
        )
    )
    documents = build_document_world(
        world, WeasyPrintInvoiceDocumentRendererAdapter()
    ).documents
    invoice = world.testbed.invoices(world.business.id)[0]

    for kind in BillingDocumentKind:
        document = documents.produce(
            world.business, invoice, kind, LanguageTag(language)
        )

        assert document.content.startswith(b"%PDF-")
        assert b"%%EOF" in document.content[-64:]
        assert len(document.content) > MIN_PDF_BYTES


def test_the_pdf_engine_fetches_nothing_the_page_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[object] = []

    def record_open(self: object, request: object, *args: Any, **kwargs: Any) -> None:
        del self, args, kwargs
        opened.append(request)
        raise OSError("no network in tests")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", record_open)
    html = BillingDocumentHtml(
        "<html><head>"
        '<link rel="stylesheet" href="https://evil.example/style.css">'
        "</head><body><p>Invoice</p>"
        '<img src="http://169.254.169.254/latest/meta-data">'
        '<img src="file:///etc/passwd"></body></html>'
    )

    pdf = WeasyPrintInvoiceDocumentRendererAdapter().render(html)

    assert pdf.startswith(b"%PDF-")
    assert opened == []


def test_an_engine_failure_is_an_external_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import weasyprint

    def broken_html(**kwargs: Any) -> None:
        del kwargs
        raise RuntimeError("Pango is missing")

    monkeypatch.setattr(weasyprint, "HTML", broken_html)

    with pytest.raises(ExternalServiceError, match="PDF could not be made"):
        WeasyPrintInvoiceDocumentRendererAdapter().render(
            BillingDocumentHtml("<p>Invoice</p>")
        )
