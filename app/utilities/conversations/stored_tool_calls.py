"""Which tool calls a stored message may name in this release."""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.typings.maintenance.constrained_strings import ReleaseGateName
from app.utilities.storage.release_gates import (
    DECLINE_RECORDING_GATE,
    OFFER_CHOICES_GATE,
    PAYMENT_LINK_TOOL_GATE,
    is_gate_open,
)

# Tools a stored message names only once their release gate is open.
GATED_TOOLS: tuple[tuple[AssistantToolName, ReleaseGateName], ...] = (
    (AssistantToolName.OFFER_CHOICES, OFFER_CHOICES_GATE),
    (AssistantToolName.SEND_PAYMENT_LINK, PAYMENT_LINK_TOOL_GATE),
    (AssistantToolName.DECLINE_RECORDING, DECLINE_RECORDING_GATE),
)


def storable_tool_calls(records: Sequence[ToolCallRecord]) -> list[ToolCallRecord]:
    """
    Every call, except offer_choices, send_payment_link and
    decline_recording while their release gates are closed: the release
    before cannot read those tool names yet; the reply keeps the options it
    offered in its own `choices` and the payment line in its text, and the
    voice platform's report of the call names a declined recording.
    """

    withheld: set[AssistantToolName] = {
        tool for tool, gate in GATED_TOOLS if not is_gate_open(gate)
    }
    return [record for record in records if record.tool_name not in withheld]
