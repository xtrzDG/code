"""
A record of business B for the privacy operations of the matrix: a READY
full export whose archive is kept (the demo asks for none), so its owner
can ask for a one-time download link.
"""

from typing import Any

from typed_time_provider import Microseconds

from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.strings import ExportArchivePath
from tests.e2e.harness import Workshop

FAR_FUTURE: Microseconds = Microseconds(2**62)


def privacy_path_values(
    workshop: Workshop,
    storage_scope: Any,
    business_id: str,
) -> dict[str, str]:
    """export_id: a ready export of business B, kept until far in the future."""

    business_key = BusinessId(business_id)
    export = BusinessExportDocument(
        business_id=business_key,
        language=LanguageTag("en"),
        status=BusinessExportStatus.READY,
        archive_path=ExportArchivePath(f"{business_id}/matrix-export.zip"),
        expires_at=FAR_FUTURE,
    )
    with storage_scope.scoped_to_business(business_key):
        workshop.container.repositories.business_export_repo().save(export)

    return {"export_id": str(export.id)}
