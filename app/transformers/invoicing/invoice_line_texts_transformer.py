from babel.numbers import format_decimal

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.billing import InvoiceKind
from app.schemas.domain.billing_profiles import InvoiceLineText
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    BILLING_PERIOD_NAMES,
    PAUSE_PERIOD_NAME,
    SERVICE_NAME,
    SETUP_FEE_LINE,
    fill_placeholders,
)
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.localization.localized_texts import build_localized_text

SERVICE_PERIOD_ITEM: LocalizedText = build_localized_text(
    en="{service} — {plan}, {billing_period}",
    ru="{service} — {plan}, {billing_period}",
    ka="{service} — {plan}, {billing_period}",
)
USAGE_OVERAGE_ITEM: LocalizedText = build_localized_text(
    en="{service} — {minutes} call minutes above the package",
    ru="{service} — {minutes} мин. звонков сверх пакета",
    ka="{service} — პაკეტს ზემოთ {minutes} წუთი ზარი",
)


class InvoiceLineTextsTransformer(
    TransformerContract[InvoiceDescriptionInput, list[InvoiceLineText]]
):
    """
    The invoice line in every language the invoice and receipt PDFs are
    written in (English, Russian, Georgian), without its dates, which the
    PDF and the cabinet print beside it: the service (concept tax rule: a
    "call and message handling service", never a licence), then the plan
    and its billing period (or, for a month of a seasonal pause, the
    pause), "setup", or the call minutes above the package. Worded once,
    when the invoice is issued, so a PDF in any of these languages never
    mixes in another one.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def transform(self, input_data: InvoiceDescriptionInput) -> list[InvoiceLineText]:
        return [
            InvoiceLineText(language=language, text=self._word(input_data, language))
            for language in SERVICE_NAME.values
        ]

    def _word(
        self, input_data: InvoiceDescriptionInput, language: LanguageTag
    ) -> InvoiceDescription:
        service: str = self._say(SERVICE_NAME, language)
        if input_data.kind is InvoiceKind.SETUP_FEE:
            return self._fill(SETUP_FEE_LINE, language, {"service": service})

        if input_data.kind is InvoiceKind.USAGE_OVERAGE:
            minutes: str = format_decimal(
                int(input_data.overage_voice_minutes or 0),
                locale=require_babel_locale(language),
            )
            return self._fill(
                USAGE_OVERAGE_ITEM, language, {"service": service, "minutes": minutes}
            )

        return self._fill(
            SERVICE_PERIOD_ITEM,
            language,
            {
                "service": service,
                "plan": self._say(input_data.plan_names, language),
                "billing_period": self._say(
                    PAUSE_PERIOD_NAME
                    if input_data.is_pause_period
                    else BILLING_PERIOD_NAMES[input_data.billing_period],
                    language,
                ),
            },
        )

    def _say(self, text: LocalizedText, language: LanguageTag) -> str:
        return str(self._localized_text_resolver.resolve(text, language))

    def _fill(
        self, template: LocalizedText, language: LanguageTag, values: dict[str, str]
    ) -> InvoiceDescription:
        return InvoiceDescription(
            fill_placeholders(self._say(template, language), values)
        )
