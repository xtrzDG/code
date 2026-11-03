"""
The assistant's actions an owner (for the business) or a platform admin
(for every business) may switch off at run time (AI-10): the tools that
change something for the customer or send something. A switched-off tool
is refused when the model asks for it, with a result that tells the model
to take a request or pass the customer to a colleague instead, so a
misbehaving action stops within one turn and without a new version.

Reading tools (search, prices, availability, the customer's bookings) and
the ways out (a handoff, an unanswered question, a caller's refusal of
the recording) always stay: switching them off would leave the customer
without an answer or a person.
"""

from collections.abc import Iterable

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.exceptions.application_errors import ValidationFailedError

SWITCHABLE_TOOLS: tuple[AssistantToolName, ...] = (
    AssistantToolName.CREATE_BOOKING,
    AssistantToolName.RESCHEDULE_BOOKING,
    AssistantToolName.CANCEL_BOOKING,
    AssistantToolName.JOIN_WAITLIST,
    AssistantToolName.CREATE_LEAD,
    AssistantToolName.SEND_LINK,
    AssistantToolName.SEND_PAYMENT_LINK,
)
SWITCHED_OFF_RESULT: str = (
    "Not run: {tool} is switched off for now. Do not promise it; take the "
    "customer's request (create_lead) if that is still on, or offer to pass "
    "them to a colleague (handoff_to_human)."
)


def check_switchable(tools: Iterable[AssistantToolName]) -> list[AssistantToolName]:
    """
    The tools in SWITCHABLE_TOOLS order, each once.

    Raises:
        ValidationFailedError: a tool that may not be switched off.
    """

    chosen: set[AssistantToolName] = set(tools)
    kept_on: set[AssistantToolName] = chosen - set(SWITCHABLE_TOOLS)
    if kept_on:
        names: str = ", ".join(sorted(str(tool) for tool in kept_on))
        raise ValidationFailedError(f"These tools cannot be switched off: {names}.")

    return [tool for tool in SWITCHABLE_TOOLS if tool in chosen]
