"""
The release gates of the phone tool send_call_transcript (ACC-03).

Open from this release (the release before it reads the name): every
call's conversation offers the tool and the message that records a voice
tool call keeps it; no version lists it (conversation tools are no
version's). The post-call flow texts the caller the transcript from the
voice platform's report of the finished call either way; calls need a
phone line.
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
        is_open=True,
    ),
    ReleaseGate(
        name=CALL_TRANSCRIPT_TOOL_GATE,
        collection_name=DocumentCollectionName("messages"),
        path=StoredEnumPath("tool_calls[].tool_name"),
        values=[CALL_TRANSCRIPT_TOOL],
        is_open=True,
    ),
)
