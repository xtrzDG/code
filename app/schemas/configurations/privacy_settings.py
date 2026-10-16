from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_integers import ExportDownloadLinkMinutes

DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES: int = 10


class PrivacySettings(ImmutableDTO):
    """
    Data-subject rights and exports.

    `suppression_list_key` (SUPPRESSION_LIST_KEY) is the platform key the
    suppression list hashes customers' numbers and accounts under. Set it
    once and never change it: an entry hashed under another key no longer
    matches, so the customer would be messaged again. Without it the key
    derives from ENCRYPTION_KEY (a rotation of that key would then lose the
    list; the API warns at start), and in development from a fixed text.

    `export_download_link_minutes` (EXPORT_DOWNLOAD_LINK_MINUTES, 1 to 10,
    default 10): how long a one-time download link of a full business export
    works. The archive itself is kept for a day.
    """

    suppression_list_key: PlatformSecret | None = Field(default=None, repr=False)
    export_download_link_minutes: ExportDownloadLinkMinutes = ExportDownloadLinkMinutes(
        DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES
    )
