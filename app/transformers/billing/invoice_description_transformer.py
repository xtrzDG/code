from datetime import date, timedelta

from babel.dates import format_date
from babel.numbers import format_decimal

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.billing import InvoiceKind
from app.schemas.dto.billing_ledger import InvoiceDescriptionInput
from app.schemas.typings.billing.strings import InvoiceDescription
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    BILLING_PERIOD_NAMES,
    SERVICE_NAME,
    SERVICE_PERIOD_LINE,
    SETUP_FEE_LINE,
    USAGE_OVERAGE_LINE,
    fill_placeholders,
    select_text_language,
)
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.localization.babel_locales import require_babel_locale

DATE_FORMAT: str = "medium"


class InvoiceDescriptionTransformer(
    TransformerContract[InvoiceDescriptionInput, InvoiceDescription]
):
    """
    Invoice line in the owner's language (English, Russian or Georgian;
    other languages read English).

    Always the service wording of the concept's tax rule:
    "Call and message handling service — Voice + chat, monthly,
    Oct 1, 2026 – Oct 31, 2026"; the setup fee reads "... — setup". The
    period shows the local calendar days it covers, the last one inclusive;
    an overage line names the minutes above the package of its month.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def transform(self, input_data: InvoiceDescriptionInput) -> InvoiceDescription:
        language: LanguageTag = select_text_language(SERVICE_NAME, input_data.language)
        service: str = str(
            self._localized_text_resolver.resolve(SERVICE_NAME, language)
        )
        if input_data.kind is InvoiceKind.SETUP_FEE:
            return InvoiceDescription(
                fill_placeholders(
                    str(
                        self._localized_text_resolver.resolve(SETUP_FEE_LINE, language)
                    ),
                    {"service": service},
                )
            )

        first_day: date = to_local_datetime(
            input_data.period_start,
            input_data.timezone,
        ).date()
        last_day: date = (
            to_local_datetime(input_data.period_end, input_data.timezone)
            - timedelta(microseconds=1)
        ).date()
        babel_locale = require_babel_locale(language)
        start_text: str = format_date(
            first_day,
            format=DATE_FORMAT,
            locale=babel_locale,
        )
        end_text: str = format_date(
            max(last_day, first_day),
            format=DATE_FORMAT,
            locale=babel_locale,
        )
        if input_data.kind is InvoiceKind.USAGE_OVERAGE:
            return InvoiceDescription(
                fill_placeholders(
                    str(
                        self._localized_text_resolver.resolve(
                            USAGE_OVERAGE_LINE,
                            language,
                        )
                    ),
                    {
                        "service": service,
                        "minutes": format_decimal(
                            int(input_data.overage_voice_minutes or 0),
                            locale=babel_locale,
                        ),
                        "start": start_text,
                        "end": end_text,
                    },
                )
            )

        return InvoiceDescription(
            fill_placeholders(
                str(
                    self._localized_text_resolver.resolve(SERVICE_PERIOD_LINE, language)
                ),
                {
                    "service": service,
                    "plan": str(
                        self._localized_text_resolver.resolve(
                            input_data.plan_names,
                            language,
                        )
                    ),
                    "billing_period": str(
                        self._localized_text_resolver.resolve(
                            BILLING_PERIOD_NAMES[input_data.billing_period],
                            language,
                        )
                    ),
                    "start": start_text,
                    "end": end_text,
                },
            )
        )
