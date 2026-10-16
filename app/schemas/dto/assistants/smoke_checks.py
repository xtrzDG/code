"""
The quick check of "Apply changes": the scenarios the changes touch and a
few core ones, instead of every scenario in every language.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import LanguageTag


class SmokeScenarioPick(ImmutableDTO):
    """One scenario kind of the quick check, in one language."""

    kind: AutotestScenarioKind
    language: LanguageTag


class SmokeCheckSelection(ImmutableDTO):
    """
    What the quick check of an apply plays: `picks` (the scenario kinds the
    changes touch and the core ones, in the default language, the core ones
    in every language too when the languages changed) and one price
    question in `price_language` for each offer item in
    `price_item_titles` (items whose price or details changed). The whole
    suite stays available from Advanced.
    """

    picks: list[SmokeScenarioPick]
    price_item_titles: list[KnowledgeTitle] = Field(
        default_factory=list[KnowledgeTitle]
    )
    price_language: LanguageTag
