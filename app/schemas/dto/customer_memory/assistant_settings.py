"""
Settings → General: whether the assistant remembers returning customers,
and the owner's controls of it (a pause, actions switched off).
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.assistants.booleans import (
    IsAssistantPaused,
    RemembersCustomers,
    SharesTeamNotesWithAssistant,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.prefixed_id import UserId


class AssistantSettingsRequest(ImmutableDTO):
    """
    The owner's choices: remember returning customers (their visits,
    bookings, open requests and what earlier conversations were about), and
    let the team's internal notes on them reach that memory. `is_paused`
    and `disabled_tools` (the owner's controls) change only when sent:
    left out, they stay as they are.
    """

    remembers_customers: RemembersCustomers = True
    shares_team_notes: SharesTeamNotesWithAssistant = False
    is_paused: IsAssistantPaused | None = None
    disabled_tools: list[AssistantToolName] | None = None


class AssistantSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class AssistantSettingsCommand(ImmutableDTO):
    """An owner changes the settings (audited)."""

    user_id: UserId
    business_id: BusinessId
    settings: AssistantSettingsRequest
    client_ip_address: ClientIpAddress | None = None


class AssistantSettingsView(ImmutableDTO):
    """The settings as stored; `updated_at` None while the defaults apply."""

    remembers_customers: RemembersCustomers
    shares_team_notes: SharesTeamNotesWithAssistant
    is_paused: IsAssistantPaused = False
    disabled_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
    updated_at: Microseconds | None = None
