"""
The release gates of the phone tool send_call_transcript (ACC-03).

Every call's conversation offers the tool, but no version stores it and no
stored message names it until the next release opens these gates (the
release before cannot read the name yet): the voice platform's report of
the finished call names the tool, and the post-call flow texts the caller
the transcript from that report.
"""

from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.typings.maintenance.constrained_strings import (
    GatedEnumValue,
    ReleaseGateName,
    StoredEnumPath,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

CALL_TRANSCRIPT_TOOL_GATE: ReleaseGateName = ReleaseGateName("send_call_transcript")
CALL_TRANSCRIPT_TOOL: GatedEnumValue = GatedEnumValue("send_call_transcript")

CALL_TOOL_RELEASE_GATES: tuple[ReleaseGate, ...] = (
    ReleaseGate(
        name=CALL_TRANSCRIPT_TOOL_GATE,
        collection_name=DocumentCollectionName("assistant_versions"),
        path=StoredEnumPath("tools[]"),
        values=[CALL_TRANSCRIPT_TOOL],
        is_open=False,
    ),
    ReleaseGate(
        name=CALL_TRANSCRIPT_TOOL_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[CALL_TRANSCRIPT_TOOL],
        is_open=False,
    ),
)
