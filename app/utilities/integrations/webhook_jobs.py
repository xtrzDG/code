"""The `deliver_webhook` job: its name and payload."""

from pydantic import ValidationError

from app.schemas.dto.integrations.webhook_attempts import WebhookDeliveryJob
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integrations.prefixed_id import WebhookDeliveryId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobPayloadJson

# One attempt of a webhook delivery (queued again for every retry).
DELIVER_WEBHOOK_JOB: JobName = JobName("deliver_webhook")


def encode_webhook_job(
    business_id: BusinessId, delivery_id: WebhookDeliveryId
) -> JobPayloadJson:
    return JobPayloadJson(
        WebhookDeliveryJob(
            business_id=business_id, delivery_id=delivery_id
        ).model_dump_json()
    )


def decode_webhook_job(payload: JobPayloadJson) -> WebhookDeliveryJob:
    try:
        return WebhookDeliveryJob.model_validate_json(str(payload))
    except ValidationError as error:
        raise ValidationFailedError(
            "The job payload does not name a webhook delivery."
        ) from error
