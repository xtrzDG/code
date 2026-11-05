"""Choose the models the routing adapter may call, from the settings."""

from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.contracts.llm import LlmAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.environment import DeploymentEnvironment
from app.utilities.config_helpers.llm_provider_keys import usable_fallback_model_id


def build_routing_llm_adapter(
    settings: AppSettings,
    openai_adapter: LlmAdapterContract,
    anthropic_adapter: LlmAdapterContract,
    scripted_adapter: LlmAdapterContract,
    circuit_breaker: CircuitBreakerContract,
) -> RoutingLlmAdapter:
    """
    OpenAI and Anthropic always; the scripted model (fixed answers) only
    outside production, so no id or setting can make a production customer
    talk to it; the fallback model only when its provider's key is set
    (`usable_fallback_model_id`; the startup checks report a skipped one).
    """

    is_production: bool = settings.environment is DeploymentEnvironment.PRODUCTION
    return RoutingLlmAdapter(
        openai_adapter=openai_adapter,
        anthropic_adapter=anthropic_adapter,
        scripted_adapter=None if is_production else scripted_adapter,
        circuit_breaker=circuit_breaker,
        fallback_model_id=usable_fallback_model_id(settings),
    )
