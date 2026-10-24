"""
The link a customer pays a deposit on, and the line that carries it: the
policy's page (else the business's default template) filled with the
request's amount and reference, a sealed address opened only here, and
the text in the customer's language (the line's own language decides how
the money is written, so the two always agree).
"""

from dataclasses import dataclass

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.secret_cipher import SecretCipherAdapterContract
from app.schemas.domain.deposits import DepositSettingsDocument, PaymentLink
from app.schemas.dto.billing import Money
from app.schemas.dto.deposits.deposit_amounts import DepositAmount
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deposits.constrained_strings import (
    DepositReference,
    PaymentLinkAddress,
    PaymentLinkUrl,
)
from app.schemas.typings.deposits.prefixed_id import PaymentLinkId
from app.schemas.typings.deposits.strings import DepositHoldEndText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.deposits.payment_link_addresses import render_payment_link
from app.utilities.money.money_formatting import format_money
from app.utilities.money.money_math import convert_money_to_major_units
from app.utilities.scheduling.localized_formatting import (
    choose_template_language,
    isolate,
)


def as_money(amount: DepositAmount) -> Money:
    return Money(
        amount_minor=MoneyAmountMinor(int(amount.amount_minor)),
        currency_code=amount.currency_code,
    )


def chosen_link(
    settings: DepositSettingsDocument, policy_link_id: PaymentLinkId | None
) -> PaymentLink | None:
    """The policy's page, else the default template; None when there is neither."""

    wanted: PaymentLinkId | None = policy_link_id or settings.default_payment_link_id
    return next((link for link in settings.payment_links if link.id == wanted), None)


@dataclass(frozen=True)
class LineValues:
    """What a payment line names (technical record)."""

    amount: FormattedMoneyText
    link: PaymentLinkUrl
    until: DepositHoldEndText
    reference: DepositReference


@dataclass(frozen=True)
class PaymentLines:
    secret_cipher: SecretCipherAdapterContract
    text_resolver: LocalizedTextResolverContract

    def url(
        self, link: PaymentLink, amount: DepositAmount, reference: DepositReference
    ) -> PaymentLinkUrl:
        money: Money = as_money(amount)
        return render_payment_link(
            self.address_of(link),
            convert_money_to_major_units(money),
            int(amount.amount_minor),
            amount.currency_code,
            reference,
        )

    def address_of(self, link: PaymentLink) -> PaymentLinkAddress:
        if link.sealed_address is not None:
            return PaymentLinkAddress(
                str(self.secret_cipher.decrypt(link.sealed_address))
            )

        if link.address is None:
            raise ValueError(f"Payment link {link.id} keeps no address.")

        return link.address

    def amount_text(
        self, template: LocalizedText, amount: DepositAmount, language: LanguageTag
    ) -> FormattedMoneyText:
        return format_money(
            as_money(amount), choose_template_language(template, language)
        )

    def line(
        self,
        template: LocalizedText,
        values: LineValues,
        language: LanguageTag,
    ) -> MessageText:
        """
        The template in the customer's language, the amount and reference
        isolated for right-to-left text; the link stays bare on a line of
        its own, so every messenger still recognizes it.
        """

        line_language: LanguageTag = choose_template_language(template, language)
        text: str = str(self.text_resolver.resolve(template, line_language))
        return MessageText(
            text.format(
                amount=isolate(str(values.amount), line_language),
                link=str(values.link),
                until=str(values.until),
                reference=isolate(str(values.reference), line_language),
            )
        )
