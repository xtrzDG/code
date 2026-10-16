"""
Which provider each data flow reaches under this deployment's settings, and
whether the sub-processor list covers it on a day (DPA section 8).
"""

from datetime import date

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmProvider
from app.schemas.constants.legal import ProcessorFlow
from app.schemas.dto.legal import SubprocessorEntry
from app.schemas.dto.processor_uses import (
    ConfiguredProcessorUse,
    ProcessorUse,
    UncoveredProcessorUse,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.legal.constrained_strings import ClientModuleName
from app.utilities.conversations.llm_models import resolve_llm_provider
from app.utilities.legal.subprocessor_dates import is_in_force

# The `app/clients` package of each model provider; the scripted model is
# offline and reaches nobody.
PROVIDER_CLIENT_MODULES: dict[LlmProvider, ClientModuleName] = {
    LlmProvider.OPENAI: ClientModuleName("openai"),
    LlmProvider.ANTHROPIC: ClientModuleName("anthropic"),
}
# Voice notes are transcribed by OpenAI's speech-to-text on every
# deployment with a real model (LLM_TRANSCRIBE_MODEL).
TRANSCRIPTION_CLIENT_MODULE: ClientModuleName = ClientModuleName("openai")


def quality_judge_model_id(settings: AppSettings) -> LlmModelId:
    """
    The model that scores the nightly sample of real conversations: the
    assistant's own (LLM_MODEL_ID) while QUALITY_SAMPLING_JUDGE_SAME_PROVIDER
    is on, else the judge (LLM_JUDGE_MODEL_ID).
    """

    if settings.quality.judge_same_provider:
        return settings.llm_model_id

    return settings.llm_judge_model_id


def model_client_module(model_id: LlmModelId | None) -> ClientModuleName | None:
    """The provider package a model id is sent to; None offline or unknown."""

    if model_id is None:
        return None

    provider: LlmProvider | None = resolve_llm_provider(model_id)
    return None if provider is None else PROVIDER_CLIENT_MODULES.get(provider)


def configured_client_module(
    flow: ProcessorFlow, settings: AppSettings
) -> ClientModuleName | None:
    """Where the settings send a flow; None when the flow is off or offline."""

    if flow is ProcessorFlow.ASSISTANT_REPLIES:
        return model_client_module(
            settings.llm_model_id
        ) or PROVIDER_CLIENT_MODULES.get(settings.llm_provider)

    if flow is ProcessorFlow.CLAIM_VERIFIER:
        return model_client_module(settings.reply_safety.llm_verifier_model_id)

    if flow is ProcessorFlow.CONVERSATION_SUMMARIES:
        return model_client_module(
            settings.llm_summary_model_id or settings.llm_model_id
        )

    if flow is ProcessorFlow.AUTOTEST_JUDGE:
        return model_client_module(settings.llm_judge_model_id)

    if flow is ProcessorFlow.QUALITY_SAMPLING:
        quality = settings.quality
        if int(quality.sample_percent) == 0 or int(quality.sample_budget_cents) == 0:
            return None

        return model_client_module(quality_judge_model_id(settings))

    if settings.llm_provider is LlmProvider.SCRIPTED:
        return None

    return TRANSCRIPTION_CLIENT_MODULE


def configure_uses(
    uses: list[ProcessorUse], settings: AppSettings
) -> list[ConfiguredProcessorUse]:
    return [
        ConfiguredProcessorUse(
            use=use, client_module=configured_client_module(use.flow, settings)
        )
        for use in uses
    ]


def find_uncovered_uses(
    configured: list[ConfiguredProcessorUse],
    entries: list[SubprocessorEntry],
    day: date,
) -> list[UncoveredProcessorUse]:
    """
    The configured flows no entry in force on `day` covers: an entry names
    the flow's provider package among its client modules and the flow
    among its flows, or among its chat provider flows when that package
    also writes the assistant's replies.
    """

    chat_module: ClientModuleName | None = next(
        (
            item.client_module
            for item in configured
            if item.use.flow is ProcessorFlow.ASSISTANT_REPLIES
        ),
        None,
    )
    uncovered: list[UncoveredProcessorUse] = []
    for item in configured:
        module: ClientModuleName | None = item.client_module
        if module is None:
            continue

        if not any(
            covers(entry, item.use.flow, module, chat_module)
            and is_in_force(entry, day)
            for entry in entries
        ):
            uncovered.append(
                UncoveredProcessorUse(
                    flow=item.use.flow,
                    client_module=module,
                    data_categories=item.use.data_categories,
                    provider_settings=item.use.provider_settings,
                )
            )

    return uncovered


def covers(
    entry: SubprocessorEntry,
    flow: ProcessorFlow,
    module: ClientModuleName,
    chat_module: ClientModuleName | None,
) -> bool:
    """The entry's purpose covers sending `flow` to `module`."""

    if module not in entry.client_modules:
        return False

    return flow in entry.flows or (
        flow in entry.chat_provider_flows and module == chat_module
    )
