from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import (
    AssistantToolName,
    AssistantVersionStatus,
    AutotestOutcome,
    AutotestScenarioKind,
)
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.assistants.booleans import IsAutotestRunPassed
from app.schemas.typings.assistants.constrained_floats import AutotestPassRate
from app.schemas.typings.assistants.constrained_integers import (
    AssistantVersionNumber,
)
from app.schemas.typings.assistants.constrained_strings import (
    AutotestScenarioKey,
    LlmModelId,
)
from app.schemas.typings.assistants.prefixed_id import (
    AssistantVersionId,
    AutotestRunId,
)
from app.schemas.typings.assistants.strings import AutotestFinding, SystemPromptText
from app.schemas.typings.businesses.booleans import IsVoiceEnabled
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.questionnaires.constrained_strings import FactKey
from app.schemas.typings.questionnaires.strings import FactLabel, FactValue


class BusinessFact(PersistentDocument):
    """One row of the business fact table the assistant answers from."""

    key: FactKey
    label: FactLabel
    value: FactValue


class AssistantVersionDocument(BaseDocument):
    """
    Immutable result of assembling the questionnaire with a niche template.

    Conversations are pinned to a version so their system prompt and tool set
    never change mid-conversation.
    """

    id: AssistantVersionId = Field(default_factory=AssistantVersionId)
    business_id: BusinessId
    version_number: AssistantVersionNumber
    status: AssistantVersionStatus = AssistantVersionStatus.ASSEMBLED
    niche_key: NicheKey
    model_id: LlmModelId
    system_prompt: SystemPromptText
    tools: list[AssistantToolName]
    customer_languages: list[LanguageTag]
    is_voice_enabled: IsVoiceEnabled
    facts: list[BusinessFact]
    questionnaire_revision: Microseconds
    autotest_run_id: AutotestRunId | None = None


class AutotestTranscriptLine(PersistentDocument):
    """One line of an autotest conversation."""

    author: MessageAuthor
    text: MessageText


class AutotestScenarioResult(PersistentDocument):
    """Judge verdict for one scenario in one language."""

    scenario_key: AutotestScenarioKey
    kind: AutotestScenarioKind
    language: LanguageTag
    outcome: AutotestOutcome
    findings: list[AutotestFinding] = Field(default_factory=list[AutotestFinding])
    transcript: list[AutotestTranscriptLine] = Field(
        default_factory=list[AutotestTranscriptLine]
    )


class AutotestRunDocument(BaseDocument):
    """All scenario results for one assistant version."""

    id: AutotestRunId = Field(default_factory=AutotestRunId)
    business_id: BusinessId
    assistant_version_id: AssistantVersionId
    results: list[AutotestScenarioResult] = Field(
        default_factory=list[AutotestScenarioResult]
    )
    pass_rate: AutotestPassRate
    is_passed: IsAutotestRunPassed
