"""One call from "Create an AI assistant" to a business with its setup."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.dto.businesses import BusinessView
from app.schemas.dto.setup.setup_progress import SetupView
from app.schemas.dto.setup.starter_answers import StarterAnswersView


class AssistantCreatedView(ImmutableDTO):
    """
    The new business (with its country's defaults: time zone, languages,
    currency), the guided setup ahead and the niche's starter answers to
    accept or edit.
    """

    business: BusinessView
    setup: SetupView
    starter_answers: StarterAnswersView
