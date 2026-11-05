"""The decline_recording model tool: a caller who does not want to be recorded."""

from app.registries.tools.tool_schema_parts import JsonSchema, object_schema

DECLINE_RECORDING_SPECIFICATION: tuple[str, JsonSchema] = (
    "Call this as soon as the caller says they do not want the call to be "
    "recorded, or asks to stop the recording, whenever in the call they say "
    "it. The call goes on as before: the platform deletes the call's audio "
    "after the call and keeps only a written transcript without phone, "
    "e-mail, card or account numbers. Then tell the caller, in their "
    "language and in one short sentence, that the call will not be kept as "
    "a recording, and continue helping them. Never end the call because of "
    "it.",
    object_schema({}),
)
