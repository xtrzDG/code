from base_pydantic_schemas import BaseDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import (
    ExportArchiveByteCount,
    ExportDownloadCount,
    ExportedRecordCount,
)
from app.schemas.typings.privacy.constrained_strings import ExportDownloadTokenHash
from app.schemas.typings.privacy.prefixed_id import (
    BusinessExportId,
    ExportDownloadLinkId,
)
from app.schemas.typings.privacy.strings import ExportArchivePath, ExportErrorText
from app.schemas.typings.users.prefixed_id import UserId


class BusinessExportDocument(BaseDocument):
    """
    One full export of a business's data: a ZIP with a JSON file per
    collection and the CSV tables, written by the worker into the export
    storage (`archive_path`, encrypted with the business's key) and
    downloadable through one-time links until `expires_at`, after which the
    archive is deleted (EXPIRED).

    `requested_by` is the owner who asked (None when the platform made it,
    e.g. before a business is deleted); `language` is the language of the
    tables' headings. `record_count` counts the rows and documents written.

    Version 2: `download_count`, how many times the archive was downloaded
    (at most 3; 0 by default, so version 1 rows read as they are).
    """

    schema_version: SchemaVersion = SchemaVersion("2")
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
    download_count: ExportDownloadCount = ExportDownloadCount(0)


class ExportDownloadLinkDocument(BaseDocument):
    """
    One one-time download link of a full export, asked for by an owner
    (`user_id`) after a recent sign-in or step-up. Only the token's SHA-256
    is kept (`token_hash`; the id derives from it). It works once
    (`used_at`), until `expires_at` (EXPORT_DOWNLOAD_LINK_MINUTES), and only
    with a session of that owner. The hourly export purge deletes expired
    links.
    """

    id: ExportDownloadLinkId
    business_id: BusinessId
    export_id: BusinessExportId
    user_id: UserId
    token_hash: ExportDownloadTokenHash
    expires_at: Microseconds
    used_at: Microseconds | None = None
