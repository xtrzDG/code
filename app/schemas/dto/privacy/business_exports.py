"""
Full exports of a business: the owner asks for one, the worker writes the
archive (a JSON file per collection and the CSV tables in a ZIP) into the
encrypted export storage for a day, and an owner downloads it at most three
times, each through a one-time link of their own that works for minutes.
"""

from collections.abc import Iterable

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.privacy import BusinessExportStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.privacy.constrained_integers import (
    ExportArchiveByteCount,
    ExportDownloadCount,
    ExportedRecordCount,
)
from app.schemas.typings.privacy.constrained_strings import (
    BusinessExportDownloadPath,
    BusinessExportToken,
    ExportFileName,
)
from app.schemas.typings.privacy.prefixed_id import BusinessExportId
from app.schemas.typings.privacy.strings import ExportErrorText
from app.schemas.typings.users.constrained_strings import SessionUserAgent
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
    for and finished, its size, until when its archive is kept
    (`expires_at`) and how many downloads it has left (`downloads_left`,
    of 3). `last_error` says why a FAILED export failed.

    `download_path` is deprecated and always None: a download needs a
    one-time link (POST …/business-exports/{export_id}/download-link).
    """

    id: BusinessExportId
    status: BusinessExportStatus
    requested_at: Microseconds
    finished_at: Microseconds | None = None
    expires_at: Microseconds | None = None
    archive_bytes: ExportArchiveByteCount | None = None
    record_count: ExportedRecordCount | None = None
    download_path: BusinessExportDownloadPath | None = Field(
        default=None, deprecated=True
    )
    downloads_left: ExportDownloadCount = ExportDownloadCount(0)
    last_error: ExportErrorText | None = None


class BusinessExportList(ImmutableDTO):
    """The business's latest exports, the newest first."""

    items: list[BusinessExportView] = Field(default_factory=list[BusinessExportView])


class ExportDownloadLinkCommand(ImmutableDTO):
    """
    An owner asks for a one-time link to download a READY export: owners
    only, after a recent sign-in or step-up.
    """

    user_id: UserId
    business_id: BusinessId
    export_id: BusinessExportId
    client_ip_address: ClientIpAddress | None = None


class ExportDownloadLinkView(ImmutableDTO):
    """
    The one-time download path (relative to the API) and when it stops
    working. It opens once, with a session of the owner who asked for it.
    """

    download_path: BusinessExportDownloadPath
    expires_at: Microseconds


class BusinessExportDownloadQuery(ImmutableDTO):
    """
    A download through a one-time link, by the signed-in user it was made
    for; the address and the browser go into every owner's notice.
    """

    user_id: UserId
    business_id: BusinessId
    export_id: BusinessExportId
    token: BusinessExportToken
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None


class ExportDownloadNotice(ImmutableDTO):
    """
    What every owner hears about one download of a full export: who, from
    which address and browser, and which download of the three it was.
    """

    business_id: BusinessId
    export_id: BusinessExportId
    downloaded_by: UserId
    client_ip_address: ClientIpAddress | None = None
    user_agent: SessionUserAgent | None = None
    download_number: ExportDownloadCount


class BusinessExportDownload(ImmutableDTO):
    """
    A download of an archive: its file name and its bytes in pieces, read
    and opened from the storage as the response sends them (never whole in
    the API's memory).
    """

    file_name: ExportFileName
    pieces: Iterable[bytes] = Field(repr=False)


class BusinessExportJobPayload(ImmutableDTO):
    """The queued job that writes one export's archive."""

    export_id: BusinessExportId
