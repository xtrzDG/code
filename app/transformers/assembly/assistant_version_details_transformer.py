from app.contracts.transformer_contract import TransformerContract
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.dto.assistants.assistant_views import (
    AssistantVersionDetails,
    BusinessFactView,
)


class AssistantVersionDetailsTransformer(
    TransformerContract[AssistantVersionDocument, AssistantVersionDetails]
):
    """An assistant version with its frozen instructions and fact table."""

    def transform(
        self, input_data: AssistantVersionDocument
    ) -> AssistantVersionDetails:
        return AssistantVersionDetails(
            id=input_data.id,
            business_id=input_data.business_id,
            version_number=input_data.version_number,
            status=input_data.status,
            niche_key=input_data.niche_key,
            model_id=input_data.model_id,
            tools=list(input_data.tools),
            languages=list(input_data.languages),
            default_language=input_data.default_language,
            is_voice_enabled=input_data.is_voice_enabled,
            profile_revision=input_data.profile_revision,
            voice_agent_id=input_data.voice_agent_id,
            test_score=input_data.test_score,
            autotest_run_id=input_data.autotest_run_id,
            published_at=input_data.published_at,
            created_at=input_data.created_at,
            prompt_text=input_data.prompt_text,
            phone_prompt_text=input_data.phone_prompt_text,
            facts=[
                BusinessFactView(key=fact.key, label=fact.label, value=fact.value)
                for fact in input_data.facts
            ],
        )
