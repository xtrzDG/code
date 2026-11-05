from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.assistants.booleans import (
    IsAssistantPaused,
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

    The owner's controls (AI-10): `is_paused` holds the assistant back
    (customers' messages go to the team, calls to the forwarding number)
    until the owner resumes it; `disabled_tools` are actions the assistant
    may not take for now (bookings, cancellations, links), each refused
    when the model asks for it.
    """

    # 2: `is_paused` and `disabled_tools` (optional: a version 1 row reads
    # as running with every tool). 3: the tool names know
    # send_call_transcript (a new value no switch writes; no upcaster).
    schema_version: SchemaVersion = SchemaVersion("3")
    id: AssistantSettingsId
    business_id: BusinessId
    remembers_customers: RemembersCustomers = True
    shares_team_notes: SharesTeamNotesWithAssistant = False
    is_paused: IsAssistantPaused = False
    disabled_tools: list[AssistantToolName] = Field(
        default_factory=list[AssistantToolName]
    )
