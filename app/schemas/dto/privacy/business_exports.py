"""
Full exports of a business: the owner asks for one, the worker writes the
archive (a JSON file per collection and the CSV tables in a ZIP) into the
encrypted export storage, and a signed link downloads it for a day.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import (
    ExportArchiveByteCount,
    ExportedRecordCount,
)
from app.schemas.typings.privacy.constrained_strings import (
    BusinessExportDownloadPath,
    BusinessExportToken,
    ExportFileName,
)
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.privacy.strings import ExportErrorText
from app.schemas.typings.users.prefixed_id import UserId


class StartBusinessExportRequest(ImmutableDTO):
    """`language`: of the CSV tables' headings (the cabinet's language)."""

    language: LanguageTag | None = None


class StartBusinessExportCommand(ImmutableDTO):
    """
    The owner asks for a full export: owners only, after a recent sign-in
    or step-up, audited. While one is queued or being written, asking again
    returns it.
    """

    user_id: UserId
    business_id: BusinessId
    request: StartBusinessExportRequest = Field(
        default_factory=StartBusinessExportRequest
    )
    client_ip_address: ClientIpAddress | None = None


class BusinessExportListQuery(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId


class BusinessExportView(ImmutableDTO):
    """
    One export as Settings → Privacy shows it: its state, when it was asked
    for and finished, its size, and while READY the signed download path
    (relative to the API; it works without the session until
    `expires_at`). `last_error` says why a FAILED export failed.
    """

    id: BusinessExportId
    status: BusinessExportStatus
    requested_at: Microseconds
    finished_at: Microseconds | None = None
    expires_at: Microseconds | None = None
    archive_bytes: ExportArchiveByteCount | None = None
    record_count: ExportedRecordCount | None = None
    download_path: BusinessExportDownloadPath | None = None
    last_error: ExportErrorText | None = None


class BusinessExportList(ImmutableDTO):
    """The business's latest exports, the newest first."""

    items: list[BusinessExportView] = Field(default_factory=list[BusinessExportView])


class BusinessExportDownloadQuery(ImmutableDTO):
    """A download through the signed link (no session; the token decides)."""

    business_id: BusinessId
    export_id: BusinessExportId
    token: BusinessExportToken
    client_ip_address: ClientIpAddress | None = None


class BusinessExportDownload(ImmutableDTO):
    file_name: ExportFileName
    content: bytes = Field(repr=False)


class BusinessExportJobPayload(ImmutableDTO):
    """The queued job that writes one export's archive."""

    export_id: BusinessExportId
