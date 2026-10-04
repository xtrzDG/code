"""Factories of the data-subject rights' providers that read the settings."""

from app.contracts.repositories.privacy_repositories import (
    SuppressionEntryRepoContract,
)
from app.facilitators.privacy.suppression_list_facilitator import (
    SuppressionListFacilitator,
)
from app.schemas.configurations.app_settings import AppSettings
from app.utilities.privacy.suppression_digests import derive_suppression_key


def build_suppression_list(
    settings: AppSettings,
    suppression_entry_repo: SuppressionEntryRepoContract,
) -> SuppressionListFacilitator:
    """The list keyed by SUPPRESSION_LIST_KEY (or its fallbacks)."""

    return SuppressionListFacilitator(
        suppression_entry_repo=suppression_entry_repo,
        suppression_key=derive_suppression_key(
            settings.privacy.suppression_list_key, settings.encryption_key
        ),
    )
