"""
The processor uses as data: every flow of personal data from the platform
to an outside model provider, the settings that choose the provider and
what the flow sends. The sub-processor list (`subprocessor_catalog.py`)
must cover each configured flow with an entry in force: a new flow, or an
old flow sent to a new provider, is announced to owners first (DPA 8.3).
"""

from app.schemas.constants.legal import ProcessorDataCategory, ProcessorFlow
from app.schemas.dto.processor_uses import ProcessorUse
from app.schemas.typings.legal.strings import ProcessorUseDescription
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName


def settings(*names: str) -> list[EnvironmentVariableName]:
    return [EnvironmentVariableName(name) for name in names]


PROCESSOR_USES: tuple[ProcessorUse, ...] = (
    ProcessorUse(
        flow=ProcessorFlow.ASSISTANT_REPLIES,
        provider_settings=settings("LLM_PROVIDER", "LLM_MODEL_ID"),
        data_categories=[
            ProcessorDataCategory.CUSTOMER_MESSAGES,
            ProcessorDataCategory.BUSINESS_KNOWLEDGE,
            ProcessorDataCategory.BOOKING_DETAILS,
        ],
        description=ProcessorUseDescription(
            "The assistant writes each reply to a customer"
        ),
    ),
    ProcessorUse(
        flow=ProcessorFlow.CLAIM_VERIFIER,
        provider_settings=settings("LLM_VERIFIER_MODEL_ID"),
        data_categories=[
            ProcessorDataCategory.CUSTOMER_MESSAGES,
            ProcessorDataCategory.BUSINESS_KNOWLEDGE,
        ],
        description=ProcessorUseDescription(
            "A cheap model checks a draft reply's prices and promises "
            "against the business's facts"
        ),
    ),
    ProcessorUse(
        flow=ProcessorFlow.CONVERSATION_SUMMARIES,
        provider_settings=settings("LLM_SUMMARY_MODEL_ID", "LLM_MODEL_ID"),
        data_categories=[
            ProcessorDataCategory.CUSTOMER_MESSAGES,
            ProcessorDataCategory.BOOKING_DETAILS,
        ],
        description=ProcessorUseDescription(
            "Summaries of calls for the team and of conversations for "
            "returning customers"
        ),
    ),
    ProcessorUse(
        flow=ProcessorFlow.AUTOTEST_JUDGE,
        provider_settings=settings("LLM_JUDGE_MODEL_ID"),
        data_categories=[
            ProcessorDataCategory.TEST_CONVERSATIONS,
            ProcessorDataCategory.BUSINESS_KNOWLEDGE,
        ],
        description=ProcessorUseDescription(
            "The judge grades the assistant's automatic checks, synthetic "
            "conversations built from the business's knowledge"
        ),
    ),
    ProcessorUse(
        flow=ProcessorFlow.QUALITY_SAMPLING,
        provider_settings=settings(
            "QUALITY_SAMPLING_JUDGE_SAME_PROVIDER",
            "LLM_JUDGE_MODEL_ID",
            "LLM_MODEL_ID",
        ),
        data_categories=[
            ProcessorDataCategory.CUSTOMER_MESSAGES,
            ProcessorDataCategory.BUSINESS_KNOWLEDGE,
        ],
        description=ProcessorUseDescription(
            "The nightly judge scores a small sample of real conversations, "
            "contacts blanked (names and free text are not)"
        ),
    ),
    ProcessorUse(
        flow=ProcessorFlow.TRANSCRIPTION,
        provider_settings=settings("LLM_TRANSCRIBE_MODEL"),
        data_categories=[ProcessorDataCategory.VOICE_NOTES],
        description=ProcessorUseDescription(
            "Customers' voice notes are turned into text"
        ),
    ),
)
