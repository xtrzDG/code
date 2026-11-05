"""The short summaries of a call staff read on the conversation card."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.calls.constrained_strings import CallSummaryText
from app.schemas.typings.localization.constrained_strings import LanguageTag


class CallSummaryView(ImmutableDTO):
    """The short summary of a call for staff, in one language."""

    language: LanguageTag
    text: CallSummaryText
