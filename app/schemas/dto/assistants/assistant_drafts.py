"""
The assistant as it would be built from what the business has now, before
anything is stored: what a new version would hold, and what the changes
not live yet are measured against.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.booleans import IsVoiceEnabled


class AssistantDraftRequest(ImmutableDTO):
    """Build the assistant of this (authorized) business from its current data."""

    business: BusinessDocument


class AssistantDraft(ImmutableDTO):
    """
    What a version built now would hold: the fact table, the tools, the
    chat instruction and (with voice in the plan) the phone instruction,
    and the profile revision it is built from. `instruction_source` is
    what the instructions were composed from, so an instruction can be
    composed again with other facts; `today` is the business-local date
    the special days were chosen by.
    """

    facts: list[BusinessFact]
    tools: list[AssistantToolName]
    prompt_text: SystemPromptText
    phone_prompt_text: SystemPromptText | None = None
    is_voice_enabled: IsVoiceEnabled
    profile_revision: Microseconds
    today: LocalDate
    instruction_source: AssistantInstructionSource
