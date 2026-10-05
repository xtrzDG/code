"""Settings → General: whether the assistant remembers returning customers."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.assistants.booleans import (
    RemembersCustomers,
    SharesTeamNotesWithAssistant,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId


class AssistantSettingsRequest(ImmutableDTO):
    """
    The owner's choices: remember returning customers (their visits,
    bookings, open requests and what earlier conversations were about), and
    let the team's internal notes on them reach that memory.
    """

    remembers_customers: RemembersCustomers = True
    shares_team_notes: SharesTeamNotesWithAssistant = False


class AssistantSettingsQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class AssistantSettingsCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    settings: AssistantSettingsRequest


class AssistantSettingsView(ImmutableDTO):
    """The settings as stored; `updated_at` None while the defaults apply."""

    remembers_customers: RemembersCustomers
    shares_team_notes: SharesTeamNotesWithAssistant
    updated_at: Microseconds | None = None
