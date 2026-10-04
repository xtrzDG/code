from babel.dates import format_date

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.billing import Money
from app.schemas.dto.invoicing import BillingDocumentEmailInput
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    fill_placeholders,
    select_text_language,
)
from app.transformers.invoicing import billing_document_texts as texts
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.money.money_formatting import format_money


class BillingDocumentEmailTransformer(
    TransformerContract[BillingDocumentEmailInput, MessageText]
):
    """
    The e-mail that brings a paid invoice and its receipt to the billing
    contact, in English, Russian or Georgian (the first line becomes the
    subject): what was received and when, and where to download the PDFs
    again.

    Raises:
        ConflictError: the invoice is not numbered or not paid.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def transform(self, input_data: BillingDocumentEmailInput) -> MessageText:
        invoice = input_data.invoice
        if invoice.number is None or invoice.paid_at is None:
            raise ConflictError("Only a numbered, paid invoice has a receipt.")

        language: LanguageTag = select_text_language(
            texts.RECEIPT_EMAIL_BODY, input_data.language
        )
        paid_day: str = format_date(
            to_local_datetime(invoice.paid_at, input_data.timezone).date(),
            format="medium",
            locale=require_babel_locale(language),
        )
        amount: str = str(
            format_money(
                Money(
                    amount_minor=invoice.amount_minor,
                    currency_code=invoice.currency_code,
                ),
                language,
            )
        )
        lines: list[str] = [
            self._say(
                texts.RECEIPT_EMAIL_SUBJECT, language, number=str(invoice.number)
            ),
            self._say(
                texts.RECEIPT_EMAIL_BODY,
                language,
                business=str(input_data.business_name),
                amount=amount,
                date=paid_day,
            ),
            self._say(texts.RECEIPT_EMAIL_HINT, language),
        ]
        return MessageText("\n".join(lines))

    def _say(self, text: LocalizedText, language: LanguageTag, **values: str) -> str:
        return fill_placeholders(
            str(self._localized_text_resolver.resolve(text, language)), values
        )
