"""
The owner's payment page: only an https address of a public payment site,
no user name, placeholders only the platform fills; a page whose query
carries a key is kept sealed and shown without it; a customer's link has
its amount and reference filled in and encoded.
"""

from decimal import Decimal

import pytest

from app.schemas.constants.deposits import PaymentLinkKind
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.deposits.constrained_strings import (
    DepositReference,
    PaymentLinkAddress,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.deposits.payment_link_addresses import (
    render_payment_link,
    vet_payment_link,
)

TEMPLATE: PaymentLinkKind = PaymentLinkKind.TEMPLATE
STATIC: PaymentLinkKind = PaymentLinkKind.STATIC


def refusal_codes(address: str, kind: PaymentLinkKind) -> list[str]:
    with pytest.raises(ValidationFailedError) as raised:
        vet_payment_link(address, kind)
    return [str(reason.code) for reason in raised.value.reasons]


def test_a_fixed_https_page_is_kept_as_entered() -> None:
    vetted = vet_payment_link("  https://pay.example.com/bistro  ", STATIC)

    assert str(vetted.address) == "https://pay.example.com/bistro"
    assert str(vetted.host) == "pay.example.com"
    assert vetted.is_secret is False


@pytest.mark.parametrize(
    "address",
    [
        "http://pay.example.com/deposit",
        "ftp://pay.example.com/deposit",
        "javascript:alert(1)",
        "pay.example.com/deposit",
    ],
)
def test_only_https_is_accepted(address: str) -> None:
    assert refusal_codes(address, STATIC) == ["link_not_https"]


@pytest.mark.parametrize(
    "address",
    [
        "https://owner:secret@pay.example.com/deposit",
        "https://localhost/deposit",
        "https://127.0.0.1/deposit",
        "https://10.0.0.8/deposit",
        "https://{amount}.example.com/deposit",
        "https:///deposit",
    ],
)
def test_private_or_unnamed_hosts_are_refused(address: str) -> None:
    assert refusal_codes(address, STATIC) == ["link_invalid"]


def test_a_fixed_page_has_no_placeholders() -> None:
    codes = refusal_codes("https://pay.example.com/d?sum={amount}", STATIC)

    assert codes == ["template_invalid"]


def test_a_template_must_pass_the_amount() -> None:
    codes = refusal_codes("https://pay.example.com/d?ref={reference}", TEMPLATE)

    assert codes == ["template_invalid"]


def test_a_template_names_only_known_placeholders() -> None:
    codes = refusal_codes(
        "https://pay.example.com/d?sum={amount}&to={customer_phone}", TEMPLATE
    )

    assert codes == ["template_invalid"]


def test_a_page_with_a_key_in_its_query_is_sealed_and_previewed_without_it() -> None:
    vetted = vet_payment_link(
        "https://checkout.example.com/pay?token=test-token-0000&sum={amount}",
        TEMPLATE,
    )

    assert vetted.is_secret is True
    assert "test-token-0000" not in str(vetted.preview)
    assert str(vetted.preview) == "https://checkout.example.com/pay (…)"


def test_the_link_fills_and_encodes_the_amount_and_reference() -> None:
    url = render_payment_link(
        PaymentLinkAddress(
            "https://pay.example.com/d?sum={amount}&m={amount_minor}"
            "&cur={currency}&ref={reference}"
        ),
        Decimal("120.50"),
        12050,
        CurrencyCode("GEL"),
        DepositReference("DK7Q3M9X"),
    )

    assert str(url) == (
        "https://pay.example.com/d?sum=120.50&m=12050&cur=GEL&ref=DK7Q3M9X"
    )


def test_a_currency_without_minor_units_passes_whole_amounts() -> None:
    url = render_payment_link(
        PaymentLinkAddress("https://pay.example.com/d?sum={amount}"),
        Decimal("5000"),
        5000,
        CurrencyCode("JPY"),
        DepositReference("DK7Q3M9X"),
    )

    assert str(url) == "https://pay.example.com/d?sum=5000"
