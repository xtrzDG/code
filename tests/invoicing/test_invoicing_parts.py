"""The small parts of invoicing: keys, parties, masked cards and refusals."""

import pytest
from typed_time_provider import Microseconds

from app.adapters.payments.flitt_payment_gateway_adapter import read_card
from app.schemas.constants.billing import InvoiceKind, InvoiceStatus
from app.schemas.constants.invoicing import BillingDocumentKind
from app.schemas.domain.billing import InvoiceDocument
from app.schemas.dto.billing_cabinet import BillingOverviewQuery
from app.schemas.dto.invoicing import BillingDocumentEmailInput, BillingDocumentPrintout
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.invoicing.constrained_integers import (
    InvoiceSequenceNumber,
    InvoiceYear,
)
from app.schemas.typings.invoicing.constrained_strings import InvoiceSeries
from app.schemas.typings.localization.constrained_strings import (
    LanguageTag,
    TimezoneName,
)
from app.transformers.invoicing.billing_document_email_transformer import (
    BillingDocumentEmailTransformer,
)
from app.utilities.billing.invoice_parties import legal_name_of_business
from app.utilities.billing.invoicing_keys import (
    build_counter_key,
    build_invoice_number,
)
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.billing.paid_world import checkout, payment_order
from tests.invoicing.document_world import HtmlEchoRenderer, build_document_world
from tests.invoicing.invoicing_world import build_seller_trial

# 2026-12-31 22:30 UTC: already 2027-01-01 02:30 in Tbilisi.
NEW_YEAR_IN_TBILISI: Microseconds = Microseconds(1_798_756_200_000_000)


def test_numbers_and_counter_keys() -> None:
    series = InvoiceSeries("AW")

    assert str(build_counter_key(series, InvoiceYear(2026))) == "AW:2026"
    assert str(
        build_invoice_number(series, InvoiceYear(2026), InvoiceSequenceNumber(42))
    ) == ("AW-2026-000042")
    assert str(
        build_invoice_number(
            series, InvoiceYear(2026), InvoiceSequenceNumber(1_234_567)
        )
    ) == ("AW-2026-1234567")


def test_the_number_counts_in_the_year_of_the_sellers_time_zone() -> None:
    world = build_seller_trial(is_vat_registered=False)
    issuing = world.testbed.invoicing.invoice_issuing
    draft = InvoiceDocument(
        business_id=world.business.id,
        kind=InvoiceKind.USAGE_OVERAGE,
        description=InvoiceDescription("Call minutes above the package"),
        amount_minor=MoneyAmountMinor(100),
        currency_code=world.business.currency_code,
        period_start=NEW_YEAR_IN_TBILISI,
        period_end=NEW_YEAR_IN_TBILISI,
        created_at=NEW_YEAR_IN_TBILISI,
        updated_at=NEW_YEAR_IN_TBILISI,
    )

    issued = issuing.issue(world.business, draft)

    assert str(issued.number) == "AW-2027-000001"
    assert issuing.issue(world.business, issued) is issued


@pytest.mark.parametrize(
    ("name", "legal_name"),
    [
        ("Mtsvane Ezo", "Mtsvane Ezo"),
        ("  Cafe\nBatumi\t ", "Cafe Batumi"),
        ("\x00", "—"),
        ("x" * 250, "x" * 200),
    ],
)
def test_a_business_without_billing_details_is_named_on_one_line(
    name: str, legal_name: str
) -> None:
    world = build_seller_trial(is_vat_registered=False)
    business = world.business.model_copy(update={"name": BusinessName(name)})

    assert str(legal_name_of_business(business)) == legal_name


@pytest.mark.parametrize(
    ("masked_card", "card_type", "brand", "digits"),
    [
        ("444455XXXXXX1111", "VISA", "VISA", "1111"),
        ("5375 41** **** 0003", " MasterCard ", "MasterCard", "0003"),
        ("444455XXXXXX11X1", "VISA", "VISA", None),
        (None, "VISA", "VISA", None),
        ("444455XXXXXX1111", "", None, "1111"),
    ],
)
def test_only_the_payment_system_and_the_last_four_digits_are_kept(
    masked_card: str | None, card_type: str, brand: str | None, digits: str | None
) -> None:
    card = read_card(masked_card, card_type)

    assert card is not None
    assert (None if card.brand is None else str(card.brand)) == brand
    assert (None if card.last_digits is None else str(card.last_digits)) == digits


def test_no_card_details_means_no_card() -> None:
    assert read_card(None, None) is None
    assert read_card(42, "") is None


def test_documents_need_a_number_and_receipts_a_payment() -> None:
    world = build_seller_trial(is_vat_registered=False)
    checkout(world)
    invoice = world.testbed.invoices(world.business.id)[0]
    documents = build_document_world(world, HtmlEchoRenderer())
    unnumbered = invoice.model_copy(update={"number": None})

    with pytest.raises(ConflictError, match="no number"):
        documents.documents.produce(
            world.business, unnumbered, BillingDocumentKind.INVOICE, LanguageTag("en")
        )
    with pytest.raises(ConflictError, match="no number"):
        documents.layout.transform(
            BillingDocumentPrintout(
                invoice=unnumbered,
                kind=BillingDocumentKind.INVOICE,
                language=LanguageTag("en"),
                timezone=TimezoneName("Asia/Tbilisi"),
            )
        )
    with pytest.raises(ConflictError, match="paid"):
        BillingDocumentEmailTransformer(LocalizedTextResolver()).transform(
            BillingDocumentEmailInput(
                invoice=invoice,
                business_name=world.business.name,
                language=LanguageTag("en"),
                timezone=world.business.timezone,
            )
        )


def test_the_billing_page_lists_numbers_vat_and_receipts() -> None:
    world = build_seller_trial(is_vat_registered=True)
    session = checkout(world)
    world.testbed.deliver_flitt_callback(
        world.testbed.callback_parameters(payment_order(world, session), "approved")
    )

    overview = world.testbed.get_overview.run(
        BillingOverviewQuery(
            user_id=world.owner.id,
            business_id=world.business.id,
            display_language=LanguageTag("en"),
        )
    )

    [invoice] = overview.invoices
    assert str(invoice.number) == "AW-2026-000001"
    assert invoice.status is InvoiceStatus.PAID
    assert invoice.is_receipt_available
    assert invoice.paid_at is not None
    assert invoice.tax is not None and int(invoice.tax.money.amount_minor) == 9_306
    assert int(invoice.tax_rate_basis_points or 0) == 1800
    assert int(invoice.amount.money.amount_minor) == 61_006
