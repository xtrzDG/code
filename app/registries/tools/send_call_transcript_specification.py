"""The send_call_transcript model tool: a caller who wants the call in writing."""

from app.registries.tools.tool_schema_parts import JsonSchema, object_schema

SEND_CALL_TRANSCRIPT_SPECIFICATION: tuple[str, JsonSchema] = (
    "Call this when the caller asks to get this call in writing: its "
    "transcript, a written summary or what was said, for example because they "
    "cannot hear well or want to keep the details. When the result has "
    '"texted_after_call": true, tell the caller in one short sentence that '
    "the transcript of this call is texted to them right after it ends. "
    "Otherwise do not promise a message: say they can write to the business "
    "in its website chat instead, or offer to pass the request to a "
    "colleague.",
    object_schema({}),
)
