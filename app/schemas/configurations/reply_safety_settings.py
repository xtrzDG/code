from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import (
    InjectionFlagLimit,
)

DEFAULT_INJECTION_FLAG_LIMIT: int = 3


class ReplySafetySettings(ImmutableDTO):
    """
    How the reply guard checks what the assistant says beyond numbers.

    LLM_VERIFIER_MODEL_ID is the cheap model that checks the policy and
    availability claims of a reply against the business's facts and tool
    results, asked only when a reply makes such a claim (None: no claim
    check). INJECTION_FLAG_LIMIT is how many messages that look like prompt
    injection one contact may send in a day before the assistant stops
    answering them until the day passes.
    """

    llm_verifier_model_id: LlmModelId | None = None
    injection_flag_limit: InjectionFlagLimit = InjectionFlagLimit(
        DEFAULT_INJECTION_FLAG_LIMIT
    )
