"""Which tool calls a stored message may name in this release."""

from collections.abc import Sequence

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.domain.conversations import ToolCallRecord
from app.utilities.storage.release_gates import OFFER_CHOICES_GATE, is_gate_open


def storable_tool_calls(records: Sequence[ToolCallRecord]) -> list[ToolCallRecord]:
    """
    Every call, except offer_choices while its release gate is closed: the
    release before cannot read that tool name yet, and the reply keeps the
    options it offered in its own `choices`.
    """

    if is_gate_open(OFFER_CHOICES_GATE):
        return list(records)

    return [
        record
        for record in records
        if record.tool_name is not AssistantToolName.OFFER_CHOICES
    ]
