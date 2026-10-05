"""Settings → Privacy as the owner reads it."""

from app.contracts.processor_erasure import ProcessorErasureFacilitatorContract
from app.contracts.repositories.retention_repositories import (
    RetentionPurgeStateRepoContract,
)
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.retention_purges import RetentionPurgeStateDocument
from app.schemas.dto.retention import PrivacySettingsView, RetentionPurgeView


def build_privacy_settings_view(
    business: BusinessDocument,
    settings: BusinessPrivacySettingsDocument,
    purge_state_repo: RetentionPurgeStateRepoContract,
    processor_erasure: ProcessorErasureFacilitatorContract,
) -> PrivacySettingsView:
    """The retention periods, the latest purge and the processors that delete."""

    state: RetentionPurgeStateDocument = purge_state_repo.get_or_new(business.id)
    return PrivacySettingsView(
        conversation_retention_days=settings.conversation_retention_days,
        llm_turn_retention_days=settings.llm_turn_retention_days,
        recording_retention_days=business.recording_retention_days,
        last_purge=(
            None
            if state.last_run_at is None
            else RetentionPurgeView(ran_at=state.last_run_at, counts=state.last_counts)
        ),
        erasure_processors=processor_erasure.erasure_processors(),
    )
