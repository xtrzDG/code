"""Internal inputs of assembling and activating an assistant version."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistants import AssistantVersionDocument, BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.localization import CountryProfile, LanguageProfile
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.assistants.booleans import CarriesBusinessChanges
from app.schemas.typings.assistants.constrained_integers import (
    LlmPricePerMillionTokensMicroUsd,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.bookings.constrained_strings import LocalDate


class BusinessFactsSource(ImmutableDTO):
    """
    Everything the fact table is built from.

    `today` is the business-local date of the assembly; only schedule
    exceptions from that day on are listed.
    """

    business: BusinessDocument
    profile: BusinessProfileDocument
    niche: NicheTemplate
    country: CountryProfile
    language_profiles: list[LanguageProfile]
    knowledge_items: list[KnowledgeItemDocument]
    resources: list[ResourceDocument]
    schedule_exceptions: list[ScheduleExceptionDocument]
    today: LocalDate


class AssistantInstructionSource(ImmutableDTO):
    """
    Everything the instructions (system prompts) of a version, for chat and
    for the phone, are composed from. The active knowledge items give the
    overview of a big catalog whose fact table is limited.
    """

    business: BusinessDocument
    profile: BusinessProfileDocument
    niche: NicheTemplate
    country: CountryProfile
    language_profiles: list[LanguageProfile]
    facts: list[BusinessFact]
    tools: list[AssistantToolName]
    knowledge_items: list[KnowledgeItemDocument] = Field(
        default_factory=list[KnowledgeItemDocument]
    )


class AssistantVersionActivation(ImmutableDTO):
    """
    Publish an authorized version of an authorized business.

    By default activation changes only its own fields of the business as
    stored when it writes. When the caller changed the given business too
    (`carries_business_changes`, settings resuming the assistant), the whole
    given business is written with them, and only while nobody saved the
    business since the caller read it (else a stale-revision conflict).
    """

    business: BusinessDocument
    version: AssistantVersionDocument
    carries_business_changes: CarriesBusinessChanges = False


class LlmTokenPrice(ImmutableDTO):
    """List price of one model, used to estimate the cost of test calls."""

    model_id: LlmModelId
    input_price: LlmPricePerMillionTokensMicroUsd
    output_price: LlmPricePerMillionTokensMicroUsd
