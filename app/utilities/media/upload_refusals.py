"""The refusals of a website visitor's upload, each with its stable code."""

import re

from base_typed_id import BasePrefixedTypedId
from base_typed_int import BaseTypedInt
from base_typed_string import BaseTypedString

from app.schemas.constants.media import WidgetUploadRefusal
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage

DETAIL_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+\-]{0,119}$")
REFUSAL_MESSAGES: dict[WidgetUploadRefusal, str] = {
    WidgetUploadRefusal.UNSUPPORTED_TYPE: (
        "The chat takes photos (JPEG, PNG, WebP) and voice notes (WebM, Ogg, MP4)."
    ),
    WidgetUploadRefusal.TYPE_MISMATCH: (
        "The file is not the type its browser declared."
    ),
    WidgetUploadRefusal.FILE_TOO_LARGE: "The file is larger than the chat takes.",
    WidgetUploadRefusal.VOICE_TOO_LONG: (
        "The voice note is longer than the chat takes."
    ),
    WidgetUploadRefusal.UNREADABLE_FILE: (
        "The file's structure does not add up, or its length cannot be read."
    ),
    WidgetUploadRefusal.ATTACHMENT_ALREADY_SENT: (
        "The attachment already went with an earlier message."
    ),
    WidgetUploadRefusal.ATTACHMENT_UNAVAILABLE: (
        "The attachment is no longer available: attach the file again."
    ),
}


def upload_refused(
    refusal: WidgetUploadRefusal,
    detail: BaseTypedString | BaseTypedInt | BasePrefixedTypedId | None = None,
) -> ValidationFailedError:
    """
    The 422 of a refused upload; `detail` (a media type, a cap, the upload
    a message named) goes with the reason when it is a plain machine value.
    """

    message: str = REFUSAL_MESSAGES[refusal]
    text: str = (
        str(int(detail)) if isinstance(detail, BaseTypedInt) else str(detail or "")
    )
    details: list[ErrorReasonDetail] = (
        [ErrorReasonDetail(text)] if DETAIL_PATTERN.match(text) else []
    )
    return ValidationFailedError(
        message,
        reasons=[
            ErrorReason(
                code=ErrorReasonCode(refusal.value),
                message=ErrorReasonMessage(message),
                details=details,
            )
        ],
    )
