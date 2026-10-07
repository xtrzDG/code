from babel.dates import format_date
from babel.numbers import format_decimal

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.billing import BillingNoticeKind, PackageMetric
from app.schemas.dto.billing import Money
from app.schemas.dto.billing_ledger import BillingNotice
from app.schemas.dto.localization import LocalizedText
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    DIALOGS_WARNING,
    FULL_SERVICE_DEADLINE,
    NOTICE_TEXTS,
    VOICE_MINUTES_WARNING,
    fill_placeholders,
    select_text_language,
)
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.localization.babel_locales import require_babel_locale
from app.utilities.money.money_formatting import format_money

DATE_FORMAT: str = "long"


class BillingNoticeTransformer(TransformerContract[BillingNotice, MessageText]):
    """
    Billing message to an owner in English, Russian or Georgian (other
    languages read English). Amounts, numbers and dates are formatted in the
    language the text is shown in; dates are local to the business.

    Payment problems with a deadline add when full service ends; a pause
    that begins names the day it ends (its `deadline`); the usage warning
    names the used share, the counts and, for minutes, the price of a
    minute above the package.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._localized_text_resolver: LocalizedTextResolverContract = (
            localized_text_resolver
        )

    def transform(self, input_data: BillingNotice) -> MessageText:
        if input_data.kind is BillingNoticeKind.PACKAGE_USAGE_WARNING:
            return self._render_usage_warning(input_data)

        template: LocalizedText = NOTICE_TEXTS[input_data.kind]
        language: LanguageTag = select_text_language(template, input_data.language)
        values: dict[str, str] = {"business": str(input_data.business_name)}
        if input_data.amount is not None:
            values["amount"] = str(format_money(input_data.amount, language))

        if input_data.deadline is not None:
            values["date"] = format_date(
                to_local_datetime(input_data.deadline, input_data.timezone).date(),
                format=DATE_FORMAT,
                locale=require_babel_locale(language),
            )

        text: str = fill_placeholders(self._resolve(template, language), values)
        if input_data.deadline is not None and input_data.kind in {
            BillingNoticeKind.PAYMENT_FAILED,
            BillingNoticeKind.TRIAL_ENDED_UNPAID,
            BillingNoticeKind.RENEWAL_MISSED,
            BillingNoticeKind.OVERAGE_INVOICED,
        }:
            text += fill_placeholders(
                self._resolve(FULL_SERVICE_DEADLINE, language), values
            )

        return MessageText(text)

    def _render_usage_warning(self, notice: BillingNotice) -> MessageText:
        if notice.usage_percent is None or notice.metric is None:
            raise ValidationFailedError("A usage warning needs a metric and a share.")

        is_voice: bool = notice.metric is PackageMetric.VOICE_MINUTES
        template: LocalizedText = VOICE_MINUTES_WARNING if is_voice else DIALOGS_WARNING
        language: LanguageTag = select_text_language(template, notice.language)
        used: int = int(
            (notice.used_voice_minutes if is_voice else notice.used_dialogs) or 0
        )
        included: int = int(
            (notice.included_voice_minutes if is_voice else notice.included_dialogs)
            or 0
        )
        babel_locale = require_babel_locale(language)
        values: dict[str, str] = {
            "business": str(notice.business_name),
            "percent": str(int(notice.usage_percent)),
            "used": format_decimal(used, locale=babel_locale),
            "included": format_decimal(included, locale=babel_locale),
        }
        overage_price: Money | None = notice.overage_price_per_minute
        if overage_price is not None:
            values["price"] = str(format_money(overage_price, language))

        return MessageText(fill_placeholders(self._resolve(template, language), values))

    def _resolve(self, text: LocalizedText, language: LanguageTag) -> str:
        return str(self._localized_text_resolver.resolve(text, language))
