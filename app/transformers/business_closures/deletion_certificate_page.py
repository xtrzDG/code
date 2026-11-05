"""The texts, dates and counts of one deletion certificate, all in its language."""

from datetime import UTC, datetime, timedelta
from html import escape

from babel import Locale
from babel.dates import format_datetime
from babel.numbers import format_decimal
from typed_time_provider import Microseconds

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.schemas.domain.business_closures import BusinessDeletionDocument
from app.schemas.dto.business_closures.deletion_certificates import (
    DeletionCertificateSource,
)
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    fill_placeholders,
    select_text_language,
)
from app.transformers.business_closures import deletion_certificate_texts as texts
from app.utilities.localization.babel_locales import require_babel_locale

UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
RIGHT_TO_LEFT_LANGUAGES: frozenset[str] = frozenset({"he", "ar", "fa", "ur"})


class DeletionCertificatePage:
    """
    One certificate in one language: every text through the catalog, every
    value escaped for HTML, every time in UTC (the business and its time
    zone are gone), every count with the language's digit grouping.
    """

    def __init__(
        self,
        resolver: LocalizedTextResolverContract,
        source: DeletionCertificateSource,
    ) -> None:
        self._resolver: LocalizedTextResolverContract = resolver
        self.entry: BusinessDeletionDocument = source.entry
        self.language: LanguageTag = select_text_language(texts.TITLE, source.language)
        self._locale: Locale = require_babel_locale(self.language)

    @property
    def direction(self) -> str:
        return (
            "rtl"
            if str(self.language).split("-")[0] in RIGHT_TO_LEFT_LANGUAGES
            else "ltr"
        )

    def say(self, text: LocalizedText, **values: str) -> str:
        """The text in this language, its placeholders filled, escaped."""

        return escape(
            fill_placeholders(str(self._resolver.resolve(text, self.language)), values)
        )

    def count(self, value: int) -> str:
        return format_decimal(value, locale=self._locale)

    def moment(self, instant: Microseconds | None) -> str:
        if instant is None:
            return self.say(texts.IN_PROGRESS)

        moment: datetime = UNIX_EPOCH + timedelta(microseconds=int(instant))
        return escape(
            format_datetime(moment, format="medium", tzinfo=UTC, locale=self._locale)
            + " UTC"
        )

    @staticmethod
    def value(text: object) -> str:
        return escape(str(text))
