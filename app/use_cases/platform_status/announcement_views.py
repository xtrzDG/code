"""Announcements as the status page, the banner and the admin see them."""

from typed_time_provider import Microseconds

from app.schemas.domain.platform_status import (
    AnnouncementMessage,
    PlatformAnnouncementDocument,
)
from app.schemas.dto.platform_announcements import (
    AnnouncementAdminView,
    AnnouncementMessageInput,
)
from app.schemas.dto.platform_status import AnnouncementView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.localization.language_tags import base_language_code

FALLBACK_LANGUAGE: str = "en"


def pick_message(
    messages: list[AnnouncementMessage], language: LanguageTag | None
) -> AnnouncementMessage:
    """The language asked for, else its base language, else English, else the first."""

    if language is not None:
        for message in messages:
            if message.language == language:
                return message
        base: str = base_language_code(language)
        for message in messages:
            if base_language_code(message.language) == base:
                return message
    for message in messages:
        if str(message.language) == FALLBACK_LANGUAGE:
            return message
    return messages[0]


def public_view(
    announcement: PlatformAnnouncementDocument,
    language: LanguageTag | None,
    now: Microseconds,
) -> AnnouncementView:
    message: AnnouncementMessage = pick_message(announcement.messages, language)
    return AnnouncementView(
        id=announcement.id,
        level=announcement.level,
        components=list(announcement.components),
        text=message.text,
        language=message.language,
        starts_at=announcement.starts_at,
        expected_end_at=announcement.expected_end_at,
        resolved_at=announcement.resolved_at,
        updated_at=announcement.updated_at,
        is_scheduled=(
            announcement.resolved_at is None and int(announcement.starts_at) > int(now)
        ),
    )


def admin_view(announcement: PlatformAnnouncementDocument) -> AnnouncementAdminView:
    return AnnouncementAdminView(
        id=announcement.id,
        level=announcement.level,
        status=announcement.status,
        components=list(announcement.components),
        messages=[
            AnnouncementMessageInput(language=message.language, text=message.text)
            for message in announcement.messages
        ],
        starts_at=announcement.starts_at,
        expected_end_at=announcement.expected_end_at,
        resolved_at=announcement.resolved_at,
        created_by=announcement.created_by,
        updated_by=announcement.updated_by,
        created_at=announcement.created_at,
        updated_at=announcement.updated_at,
    )


def stored_messages(
    messages: list[AnnouncementMessageInput],
) -> list[AnnouncementMessage]:
    return [
        AnnouncementMessage(language=message.language, text=message.text)
        for message in messages
    ]
