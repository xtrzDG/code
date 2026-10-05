"""The assistant settings of a business as the owner and the engine see them."""

from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.dto.customer_memory.assistant_settings import (
    AssistantSettingsView,
)

# Without a stored document: remember customers, keep the team's notes apart.
DEFAULT_ASSISTANT_SETTINGS: AssistantSettingsView = AssistantSettingsView(
    remembers_customers=True,
    shares_team_notes=False,
)


def view_assistant_settings(
    stored: AssistantSettingsDocument | None,
) -> AssistantSettingsView:
    """The stored settings, else the defaults."""

    if stored is None:
        return DEFAULT_ASSISTANT_SETTINGS

    return AssistantSettingsView(
        remembers_customers=stored.remembers_customers,
        shares_team_notes=stored.shares_team_notes,
        updated_at=stored.updated_at,
    )
