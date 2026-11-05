from babel.dates import format_date

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.dto.business_closures.closure_notices import ClosureNotice
from app.schemas.dto.localization import LocalizedText
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.transformers.billing.billing_texts import (
    fill_placeholders,
    select_text_language,
)
from app.transformers.business_closures.closure_texts import CLOSURE_NOTICE_TEXTS
from app.utilities.billing.billing_periods import to_local_datetime
from app.utilities.localization.babel_locales import require_babel_locale

DATE_FORMAT: str = "long"


class ClosureNoticeTransformer(TransformerContract[ClosureNotice, MessageText]):
    """
    An owner's notice about the business's closure, in the owner's cabinet
    language (English when the catalog lacks it); the deletion date is
    local to the business and written in the language the notice is in.
    """

    def __init__(self, localized_text_resolver: LocalizedTextResolverContract) -> None:
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def transform(self, input_data: ClosureNotice) -> MessageText:
        template: LocalizedText = CLOSURE_NOTICE_TEXTS[input_data.kind]
        language: LanguageTag = select_text_language(template, input_data.language)
        values: dict[str, str] = {
            "business": str(input_data.business_name),
            "actor": str(input_data.actor_name or ""),
            "date": format_date(
                to_local_datetime(input_data.delete_after, input_data.timezone).date(),
                format=DATE_FORMAT,
                locale=require_babel_locale(language),
            ),
        }
        return MessageText(
            fill_placeholders(str(self._resolver.resolve(template, language)), values)
        )
