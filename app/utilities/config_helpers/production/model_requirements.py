"""
The language models production answers with: a real provider (never the
scripted model), the key of every provider a configured model needs, and
OPENAI_API_KEY always (speech-to-text of voice notes and the menu photo
import call OpenAI whatever LLM_PROVIDER says).
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.schemas.typings.platform.strings import ProductionSettingProblem
from app.utilities.config_helpers.app_settings.llm_settings_section import (
    LLM_PROVIDER_KEY_VARIABLES,
)
from app.utilities.config_helpers.llm_provider_keys import missing_key_variable
from app.utilities.conversations.llm_models import resolve_llm_provider

# Features that call OpenAI with any chat provider.
ALWAYS_OPENAI_FEATURES: str = "voice notes (speech-to-text) and the menu photo import"


def find_model_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    if settings.llm_provider is LlmProvider.SCRIPTED:
        return [
            ProductionSettingProblem(
                "LLM_PROVIDER=scripted answers every customer with one fixed "
                "sentence: production needs openai or anthropic."
            )
        ]

    problems: list[ProductionSettingProblem] = []
    provider_key: str = LLM_PROVIDER_KEY_VARIABLES[settings.llm_provider]
    if settings.llm_provider not in settings.keyed_llm_providers:
        problems.append(
            ProductionSettingProblem(
                f"LLM_PROVIDER={settings.llm_provider.value} needs {provider_key}, "
                "which is not set."
            )
        )
    if (
        LlmProvider.OPENAI not in settings.keyed_llm_providers
        and settings.llm_provider is not LlmProvider.OPENAI
    ):
        problems.append(
            ProductionSettingProblem(
                f"OPENAI_API_KEY is not set: {ALWAYS_OPENAI_FEATURES} use "
                "OpenAI with every LLM_PROVIDER."
            )
        )
    for variable_name, model_id in configured_models(settings):
        problem: ProductionSettingProblem | None = model_problem(
            settings, variable_name, model_id
        )
        if problem is not None:
            problems.append(problem)

    return problems


def configured_models(settings: AppSettings) -> list[tuple[str, LlmModelId]]:
    """`(variable, model)` of every model production calls by its own id."""

    models: list[tuple[str, LlmModelId | None]] = [
        ("LLM_MODEL_ID", settings.llm_model_id),
        ("LLM_JUDGE_MODEL_ID", settings.llm_judge_model_id),
        ("LLM_SUMMARY_MODEL_ID", settings.llm_summary_model_id),
        ("LLM_VERIFIER_MODEL_ID", settings.reply_safety.llm_verifier_model_id),
        ("SPEND_SOFT_LIMIT_MODEL_ID", settings.spend_guard.soft_limit_model_id),
    ]
    return [(name, model_id) for name, model_id in models if model_id is not None]


def model_problem(
    settings: AppSettings, variable_name: str, model_id: LlmModelId
) -> ProductionSettingProblem | None:
    """Why production cannot call a configured model; None when it can."""

    provider: LlmProvider | None = resolve_llm_provider(model_id)
    if provider is None or provider is LlmProvider.SCRIPTED:
        return ProductionSettingProblem(
            f"{variable_name}={model_id} is not a model of OpenAI or Anthropic."
        )

    key_variable: EnvironmentVariableName | None = missing_key_variable(
        settings, model_id
    )
    if key_variable is None or key_variable == LLM_PROVIDER_KEY_VARIABLES.get(
        settings.llm_provider
    ):
        # The provider's own missing key is reported once, above.
        return None

    return ProductionSettingProblem(
        f"{variable_name}={model_id} needs {key_variable}, which is not set."
    )
