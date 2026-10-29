"""
Asking for a full business export: the record the worker fills and the
queued job that writes its archive. The owner's request uses it, and so
can any flow that must hand a business its data first (offboarding: the
platform asks, `requested_by` None).
"""

from typed_time_provider import Microseconds

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.privacy_repositories import (
    BusinessExportRepoContract,
)
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.dto.privacy.business_exports import BusinessExportJobPayload
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.strings import JobPayloadJson
from app.schemas.typings.users.prefixed_id import UserId

BUILD_BUSINESS_EXPORT_JOB: JobName = JobName("build_business_export")


def queue_business_export(
    export_repo: BusinessExportRepoContract,
    job_queue: JobQueueFacilitatorContract,
    business_id: BusinessId,
    requested_by: UserId | None,
    language: LanguageTag,
    now: Microseconds,
) -> BusinessExportDocument:
    """The QUEUED export, stored, and its job queued (one at a time per business)."""

    export = BusinessExportDocument(
        business_id=business_id,
        requested_by=requested_by,
        language=language,
        created_at=now,
        updated_at=now,
    )
    export_repo.save(export)
    job_queue.enqueue(
        BUILD_BUSINESS_EXPORT_JOB,
        JobPayloadJson(BusinessExportJobPayload(export_id=export.id).model_dump_json()),
        business_id,
        lane=JobLane.DEFAULT,
        serial_key=JobSerialKey(f"business_export:{business_id}"),
    )
    return export
