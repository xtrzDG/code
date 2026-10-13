from base_pydantic_schemas import PersistentDocument

from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.localization.constrained_strings import LanguageTag


class CallSummary(PersistentDocument):
    """The summary of a call for staff in one language (`CallDocument.summaries`)."""

    language: LanguageTag
    text: CallSummaryText
