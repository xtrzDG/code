from app.schemas.domain.billing import InvoiceDocument
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import base_language_code


def word_invoice_line(
    invoice: InvoiceDocument, language: LanguageTag
) -> InvoiceDescription:
    """
    What the invoice line says to a reader of `language`: its wording in
    that language (or its base language, "ru-RU" reads "ru") as issued,
    otherwise the line as issued in the owner language (`description`, the
    only wording an invoice from before the PDFs has).
    """

    wanted: str = base_language_code(language)
    for line in invoice.line_texts:
        if base_language_code(line.language) == wanted:
            return line.text

    return invoice.description
