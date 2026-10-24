"""The queued job that deletes a closed business, and its payload."""

from app.schemas.dto.business_closures.business_deletions import (
    DeleteBusinessJobPayload,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson

DELETE_BUSINESS_JOB: JobName = JobName("delete_business")


def deletion_payload(business_id: BusinessId) -> JobPayloadJson:
    return JobPayloadJson(
        DeleteBusinessJobPayload(business_id=business_id).model_dump_json()
    )


def deletion_serial_key(business_id: BusinessId) -> JobSerialKey:
    """One deletion of a business runs at a time, whoever queued it."""

    return JobSerialKey(f"delete_business:{business_id}")
