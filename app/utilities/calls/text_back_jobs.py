"""The job that sends a text-back, and its payload."""

from pydantic import ValidationError

from app.schemas.dto.calls.missed_calls import TextBackJobPayload
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.calls.prefixed_id import MissedCallId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson

# The message to a caller who did not get through (WhatsApp, else SMS).
SEND_TEXT_BACK_JOB: JobName = JobName("send_missed_call_text_back")


def encode_text_back_payload(missed_call_id: MissedCallId) -> JobPayloadJson:
    return JobPayloadJson(
        TextBackJobPayload(missed_call_id=missed_call_id).model_dump_json()
    )


def decode_text_back_payload(payload: JobPayloadJson) -> MissedCallId:
    try:
        return TextBackJobPayload.model_validate_json(str(payload)).missed_call_id
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name a missed call."
        ) from error
