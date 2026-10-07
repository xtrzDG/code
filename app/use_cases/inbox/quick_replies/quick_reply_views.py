"""Saved replies as the cabinet reads them, and the checks of a new text."""

from app.schemas.constants.inbox import InboxRefusalCode
from app.schemas.domain.quick_replies import QuickReply, QuickReplyLibraryDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.dto.inbox.quick_replies import (
    QuickReplyList,
    QuickReplyRequest,
    QuickReplyVariantView,
    QuickReplyView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.inbox.prefixed_id import QuickReplyId
from app.schemas.typings.platform.constrained_strings import ErrorReasonDetail
from app.use_cases.inbox.inbox_support import refusal
from app.utilities.inbox.quick_reply_templates import (
    unknown_placeholders,
    variables_in,
)

# Saved replies of one business.
MAX_QUICK_REPLIES: int = 100


def build_quick_reply_view(reply: QuickReply) -> QuickReplyView:
    return QuickReplyView(
        id=reply.id,
        shortcut=reply.shortcut,
        title=reply.title,
        variants=[
            QuickReplyVariantView(language=variant.language, text=variant.text)
            for variant in reply.variants
        ],
        variables=variables_in([str(variant.text) for variant in reply.variants]),
        created_by=reply.created_by,
        updated_at=reply.updated_at,
    )


def build_quick_reply_list(
    library: QuickReplyLibraryDocument | None,
) -> QuickReplyList:
    if library is None:
        return QuickReplyList()

    return QuickReplyList(
        items=[build_quick_reply_view(reply) for reply in library.replies]
    )


def check_texts(request: QuickReplyRequest) -> None:
    """
    ValidationFailedError when two variants share a language
    (`duplicate_language`) or a text names a variable the inbox does not
    fill (`unknown_variable`, the names as details).
    """

    languages: list[str] = [
        str(variant.language).lower() for variant in request.variants
    ]
    if len(set(languages)) != len(languages):
        raise ValidationFailedError(
            "Each language can have one text.",
            reasons=[
                refusal(
                    InboxRefusalCode.DUPLICATE_LANGUAGE,
                    "Keep one text per language.",
                )
            ],
        )

    unknown: list[str] = unknown_placeholders(
        [str(variant.text) for variant in request.variants]
    )
    if unknown:
        reason: ErrorReason = refusal(
            InboxRefusalCode.UNKNOWN_VARIABLE,
            "Use {name}, {booking_time} or {business_name}.",
        )
        raise ValidationFailedError(
            "The text names variables the inbox cannot fill: "
            + ", ".join(unknown)
            + ".",
            reasons=[
                reason.model_copy(
                    update={
                        "details": [
                            ErrorReasonDetail(name.lstrip("_")[:120])
                            for name in unknown[:10]
                            if name.lstrip("_")
                        ]
                    }
                )
            ],
        )


def check_place_in(
    library: QuickReplyLibraryDocument,
    request: QuickReplyRequest,
    replacing: QuickReplyId | None,
) -> None:
    """
    ConflictError when another saved reply has the shortcut (ignoring case,
    `shortcut_taken`) or a new one would pass the limit
    (`too_many_quick_replies`).
    """

    wanted: str = str(request.shortcut).casefold()
    if any(
        str(reply.shortcut).casefold() == wanted and reply.id != replacing
        for reply in library.replies
    ):
        raise ConflictError(
            f"Another saved reply already uses /{request.shortcut}.",
            reasons=[
                refusal(InboxRefusalCode.SHORTCUT_TAKEN, "Choose another shortcut.")
            ],
        )

    if replacing is None and len(library.replies) >= MAX_QUICK_REPLIES:
        raise ConflictError(
            f"A business keeps at most {MAX_QUICK_REPLIES} saved replies.",
            reasons=[
                refusal(
                    InboxRefusalCode.TOO_MANY_QUICK_REPLIES,
                    "Delete a saved reply you no longer use.",
                )
            ],
        )
