from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import (
    ExportArchiveByteCount,
    ExportedRecordCount,
)
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.privacy.strings import ExportArchivePath, ExportErrorText
from app.schemas.typings.users.prefixed_id import UserId


class BusinessExportDocument(BaseDocument):
    """
    One full export of a business's data: a ZIP with a JSON file per
    collection and the CSV tables, written by the worker into the export
    storage (`archive_path`, encrypted with the business's key) and
    downloadable through a signed link until `expires_at`, after which the
    archive is deleted (EXPIRED).

    `requested_by` is the owner who asked (None when the platform made it,
    e.g. before a business is deleted); `language` is the language of the
    tables' headings. `record_count` counts the rows and documents written.
    """

    id: BusinessExportId = Field(default_factory=BusinessExportId)
    business_id: BusinessId
    requested_by: UserId | None = None
    language: LanguageTag
    status: BusinessExportStatus = BusinessExportStatus.QUEUED
    archive_path: ExportArchivePath | None = None
    archive_bytes: ExportArchiveByteCount | None = None
    record_count: ExportedRecordCount | None = None
    started_at: Microseconds | None = None
    finished_at: Microseconds | None = None
    expires_at: Microseconds | None = None
    last_error: ExportErrorText | None = None
