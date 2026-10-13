"""
The owner's payment pages: what an address must be (https, a real host, no
user name or password, placeholders only the platform fills), which ones
carry a key and are kept sealed, how the cabinet shows them, and the link
one customer receives (the template filled with the request's amount and
reference, every value URL-encoded).
"""

import ipaddress
import re
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import SplitResult, parse_qsl, quote, urlsplit

from app.schemas.constants.deposits import DepositRefusalCode, PaymentLinkKind
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.deposits.constrained_strings import (
    DepositReference,
    PaymentLinkAddress,
    PaymentLinkUrl,
)
from app.schemas.typings.deposits.strings import PaymentLinkHost, PaymentLinkPreview
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.deposits.deposit_refusals import deposit_refusal

PLACEHOLDER: re.Pattern[str] = re.compile(r"\{([^{}]*)\}")
AMOUNT_PLACEHOLDERS: frozenset[str] = frozenset({"amount", "amount_minor"})
KNOWN_PLACEHOLDERS: frozenset[str] = AMOUNT_PLACEHOLDERS | {"currency", "reference"}
# Query names that carry a merchant's key rather than ordinary page options.
SECRET_PARAMETER_NAMES: frozenset[str] = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "client_secret",
        "hash",
        "key",
        "pass",
        "password",
        "private_key",
        "pwd",
        "secret",
        "sig",
        "signature",
        "token",
    }
)
LOCAL_HOST_NAMES: frozenset[str] = frozenset({"localhost", "localhost.localdomain"})


@dataclass(frozen=True)
class VettedPaymentLink:
    """An address the platform accepts, and how it is kept and shown."""

    address: PaymentLinkAddress
    host: PaymentLinkHost
    preview: PaymentLinkPreview
    is_secret: bool


def vet_payment_link(raw_address: str, kind: PaymentLinkKind) -> VettedPaymentLink:
    """
    Raises:
        ValidationFailedError: not an https address of a public host, with a
            user name, a placeholder in the host, a placeholder the platform
            does not fill, a fixed page with placeholders or a template that
            passes no amount (`reasons[].code`: DepositRefusalCode).
    """

    text: str = raw_address.strip()
    if any(character.isspace() for character in text):
        raise _invalid("A payment link may not contain spaces.")

    parts: SplitResult = urlsplit(text)
    if parts.scheme.lower() != "https":
        raise deposit_refusal(
            DepositRefusalCode.LINK_NOT_HTTPS,
            "A payment link must start with https://.",
        )

    host: str = (parts.hostname or "").lower()
    if not host or "{" in parts.netloc or "}" in parts.netloc:
        raise _invalid("A payment link needs the name of the payment site.")

    if parts.username is not None or parts.password is not None:
        raise _invalid("A payment link may not carry a user name or password.")

    if _is_local_host(host):
        raise _invalid("A payment link must point to a public payment site.")

    # The scheme and the host know no case ("Https://Pay.Example.com/…", as
    # a phone's keyboard capitalises it): kept in lower case, the rest as typed.
    typed_prefix: str = f"{parts.scheme}://{parts.netloc}"
    if not text.lower().startswith(typed_prefix.lower()):
        raise _invalid("A payment link needs the name of the payment site.")

    text = f"https://{parts.netloc.lower()}{text[len(typed_prefix) :]}"
    _check_placeholders(text, kind)
    try:
        address = PaymentLinkAddress(text)
    except ValueError as error:
        raise _invalid("A payment link needs the name of the payment site.") from error

    is_secret: bool = _carries_a_key(parts.query) or _carries_a_key(parts.fragment)
    return VettedPaymentLink(
        address=address,
        host=PaymentLinkHost(host),
        preview=PaymentLinkPreview(
            f"https://{host}{parts.path}{' (…)' if is_secret else _rest(parts)}"
        ),
        is_secret=is_secret,
    )


def render_payment_link(
    address: PaymentLinkAddress,
    amount_major: Decimal,
    amount_minor: int,
    currency_code: CurrencyCode,
    reference: DepositReference,
) -> PaymentLinkUrl:
    """
    The link one customer receives: a template's placeholders filled in
    (`{amount}` in major units with the currency's digits, `{amount_minor}`
    in minor units), a fixed page as it is.
    """

    values: dict[str, str] = {
        "amount": format(amount_major, "f"),
        "amount_minor": str(amount_minor),
        "currency": str(currency_code),
        "reference": str(reference),
    }
    return PaymentLinkUrl(
        PLACEHOLDER.sub(
            lambda match: quote(values[match.group(1)], safe=""), str(address)
        )
    )


def _check_placeholders(text: str, kind: PaymentLinkKind) -> None:
    names: set[str] = {match.group(1) for match in PLACEHOLDER.finditer(text)}
    unknown: set[str] = names - KNOWN_PLACEHOLDERS
    if unknown or text.count("{") != text.count("}"):
        raise deposit_refusal(
            DepositRefusalCode.TEMPLATE_INVALID,
            "A payment link template may use only {amount}, {amount_minor}, "
            "{currency} and {reference}.",
        )

    if kind is PaymentLinkKind.STATIC and names:
        raise deposit_refusal(
            DepositRefusalCode.TEMPLATE_INVALID,
            "A fixed payment page has no placeholders; save it as a template.",
        )

    if kind is PaymentLinkKind.TEMPLATE and not names & AMOUNT_PLACEHOLDERS:
        raise deposit_refusal(
            DepositRefusalCode.TEMPLATE_INVALID,
            "A payment link template passes the amount: {amount} or {amount_minor}.",
        )


def _carries_a_key(query: str) -> bool:
    return any(
        name.strip().lower() in SECRET_PARAMETER_NAMES
        for name, _ in parse_qsl(query, keep_blank_values=True)
    )


def _is_local_host(host: str) -> bool:
    if host in LOCAL_HOST_NAMES or host.endswith(".localhost") or "." not in host:
        return True

    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False

    return not address.is_global


def _rest(parts: SplitResult) -> str:
    """The query and fragment of an address without a key, as written."""

    return (f"?{parts.query}" if parts.query else "") + (
        f"#{parts.fragment}" if parts.fragment else ""
    )


def _invalid(message: str) -> ValidationFailedError:
    return deposit_refusal(DepositRefusalCode.LINK_INVALID, message)
