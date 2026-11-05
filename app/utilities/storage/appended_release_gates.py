"""
The release gates kept in modules of their own, appended to RELEASE_GATES
(`release_gates`): the status page's payments component (REL-06) and the
phone tool send_call_transcript (ACC-03).
"""

from app.schemas.dto.release_gates import ReleaseGate
from app.utilities.storage.call_tool_release_gates import CALL_TOOL_RELEASE_GATES
from app.utilities.storage.status_release_gates import STATUS_RELEASE_GATES

APPENDED_RELEASE_GATES: tuple[ReleaseGate, ...] = (
    *STATUS_RELEASE_GATES,
    *CALL_TOOL_RELEASE_GATES,
)
