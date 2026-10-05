from base_pydantic_schemas import BaseDocument

from app.schemas.typings.assistants.booleans import (
    RemembersCustomers,
    SharesTeamNotesWithAssistant,
)
from app.schemas.typings.assistants.prefixed_id import AssistantSettingsId
from app.schemas.typings.businesses.prefixed_id import BusinessId


class AssistantSettingsDocument(BaseDocument):
    """
    How the assistant of one business treats its customers (Settings →
    General; one document per business, the id derived from it).

    With `remembers_customers` (the default, also without a document) the
    assistant greets a returning customer, knows their upcoming bookings,
    open requests and what earlier conversations were about (summaries the
    worker writes after two quiet hours). Off: no summaries are written and
    every conversation starts from zero. `shares_team_notes` adds the
    team's internal notes on the customer's latest conversations to that
    memory; off by default, since staff write notes for each other.
    """

    id: AssistantSettingsId
    business_id: BusinessId
    remembers_customers: RemembersCustomers = True
    shares_team_notes: SharesTeamNotesWithAssistant = False
