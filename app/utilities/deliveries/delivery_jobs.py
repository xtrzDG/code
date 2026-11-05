"""Job names of the inbox and the outbox, and their payloads."""

from pydantic import ValidationError

from app.schemas.dto.deliveries import InboundEventJobPayload, OutboundMessageJobPayload
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.deliveries.prefixed_id import InboundEventId, OutboundMessageId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson

# A customer message of a messaging channel or the website widget.
PROCESS_INBOUND_MESSAGE_JOB: JobName = JobName("process_inbound_message")
# A staff message to the platform Telegram bot ("/start <code>").
PROCESS_PLATFORM_BOT_UPDATE_JOB: JobName = JobName("process_platform_bot_update")
# A finished-call report of the voice platform.
PROCESS_POST_CALL_JOB: JobName = JobName("process_post_call")
# One outbox message: an assistant reply or a staff notification.
DELIVER_OUTBOUND_JOB: JobName = JobName("deliver_outbound")


def encode_inbound_event_payload(event_id: InboundEventId) -> JobPayloadJson:
    return JobPayloadJson(InboundEventJobPayload(event_id=event_id).model_dump_json())


def decode_inbound_event_payload(payload: JobPayloadJson) -> InboundEventId:
    try:
        return InboundEventJobPayload.model_validate_json(str(payload)).event_id
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name an inbox event."
        ) from error


def encode_outbound_message_payload(
    outbound_message_id: OutboundMessageId,
) -> JobPayloadJson:
    return JobPayloadJson(
        OutboundMessageJobPayload(
            outbound_message_id=outbound_message_id
        ).model_dump_json()
    )


def decode_outbound_message_payload(payload: JobPayloadJson) -> OutboundMessageId:
    try:
        return OutboundMessageJobPayload.model_validate_json(
            str(payload)
        ).outbound_message_id
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name an outbox message."
        ) from error
