"""The uploads a website visitor's message names, checked before it is queued."""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.media_repositories import WidgetUploadRepoContract
from app.schemas.constants.media import WidgetUploadRefusal
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetSessionKey
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.schemas.typings.media.strings import ProviderMediaId, ProviderMediaType
from app.utilities.channels.widget_visitors import widget_visitor_id
from app.utilities.media.upload_refusals import upload_refused

MICROSECONDS_PER_SECOND: int = 1_000_000
# An upload waits a day for its message; the daily purge removes it after.
UPLOAD_LIFETIME_MICROSECONDS: int = 24 * 60 * 60 * MICROSECONDS_PER_SECOND


def read_message_uploads(
    widget_upload_repo: WidgetUploadRepoContract,
    business_id: BusinessId,
    session_key: WidgetSessionKey,
    upload_ids: Sequence[WidgetUploadId],
    now: Microseconds,
) -> list[WidgetUploadDocument]:
    """
    The named uploads, in the message's order, each one read in one query.

    Raises:
        ValidationFailedError: an upload named twice; one of this visitor's
            uploads already attached to a message (`attachment_already_sent`,
            a Retry after a lost answer); one that is missing, another
            business's or another visitor's, or older than a day
            (`attachment_unavailable`, the same answer for each, so ids
            cannot be probed).
    """

    if len(set(upload_ids)) != len(upload_ids):
        raise ValidationFailedError("A message names each attachment once.")

    if not upload_ids:
        return []

    found: dict[WidgetUploadId, WidgetUploadDocument] = {
        upload.id: upload
        for upload in widget_upload_repo.get_many(business_id, upload_ids)
    }
    visitor: WidgetVisitorId = widget_visitor_id(str(session_key))
    oldest: int = int(now) - UPLOAD_LIFETIME_MICROSECONDS
    uploads: list[WidgetUploadDocument] = []
    for upload_id in upload_ids:
        upload: WidgetUploadDocument | None = found.get(upload_id)
        if (
            upload is None
            or upload.visitor_id != visitor
            or int(upload.created_at) < oldest
        ):
            raise upload_refused(WidgetUploadRefusal.ATTACHMENT_UNAVAILABLE, upload_id)

        if upload.attached_at is not None:
            raise upload_refused(WidgetUploadRefusal.ATTACHMENT_ALREADY_SENT, upload_id)

        uploads.append(upload)

    return uploads


def inbound_attachment_of(upload: WidgetUploadDocument) -> InboundAttachment:
    """
    What the inbox keeps of an upload, as a messenger's webhook gives it:
    where the file is (its storage path, which the website chat's fetcher
    reads), its type and size as checked, and a voice note's length.
    """

    return InboundAttachment(
        kind=upload.kind,
        provider_media_id=ProviderMediaId(str(upload.storage_path)),
        mime_type=ProviderMediaType(str(upload.media_type)),
        declared_bytes=upload.byte_count,
        duration_seconds=upload.duration_seconds,
    )
