"""
The platform admin's announcements (POST, PATCH and GET
/v1/admin/announcements): the banner every owner sees over the cabinet
and the notice of the public status page, in each language owners read.
"""

from typing import Self

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field, model_validator
from typed_time_provider import Microseconds

from app.schemas.constants.platform_status import (
    AnnouncementLevel,
    AnnouncementStatus,
    StatusComponent,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.schemas.typings.platform_status.booleans import IsAnnouncementResolution
from app.schemas.typings.platform_status.constrained_strings import AnnouncementText
from app.schemas.typings.platform_status.prefixed_id import AnnouncementId
from app.schemas.typings.users.prefixed_id import UserId

ANNOUNCEMENT_FALLBACK_LANGUAGE: str = "en"
MAX_ANNOUNCEMENT_LANGUAGES: int = 10


class AnnouncementMessageInput(ImmutableDTO):
    """An announcement's text in one language."""

    language: LanguageTag
    text: AnnouncementText


def check_messages(messages: list[AnnouncementMessageInput]) -> None:
    """Each language once, and English always (the fallback of every reader)."""

    languages: list[str] = [str(message.language) for message in messages]
    if len(set(languages)) != len(languages):
        raise ValueError("Each language may appear only once.")
    if ANNOUNCEMENT_FALLBACK_LANGUAGE not in languages:
        raise ValueError("An announcement needs its English text.")


def check_components(
    level: AnnouncementLevel, components: list[StatusComponent]
) -> None:
    if len(set(components)) != len(components):
        raise ValueError("Each component may appear only once.")
    if level is not AnnouncementLevel.INFO and not components:
        raise ValueError(
            "Maintenance, degraded service and outages name the components they affect."
        )


class CreateAnnouncementBody(ImmutableDTO):
    """
    POST /v1/admin/announcements. `starts_at` is when it counts for its
    components (default: now; later for planned maintenance), and
    `expected_end_at` when the team expects it to be over (optional).
    """

    level: AnnouncementLevel
    components: list[StatusComponent] = Field(
        default_factory=list[StatusComponent], max_length=len(StatusComponent)
    )
    messages: list[AnnouncementMessageInput] = Field(
        min_length=1, max_length=MAX_ANNOUNCEMENT_LANGUAGES
    )
    starts_at: Microseconds | None = None
    expected_end_at: Microseconds | None = None

    @model_validator(mode="after")
    def check_announcement(self) -> Self:
        check_messages(self.messages)
        check_components(self.level, self.components)
        if (
            self.starts_at is not None
            and self.expected_end_at is not None
            and int(self.expected_end_at) <= int(self.starts_at)
        ):
            raise ValueError("An announcement is expected to end after it starts.")
        return self


class CreateAnnouncementCommand(ImmutableDTO):
    user_id: UserId
    body: CreateAnnouncementBody
    client_ip_address: ClientIpAddress | None = None


class UpdateAnnouncementBody(ImmutableDTO):
    """
    PATCH /v1/admin/announcements/{id}: a new level, components, texts or
    expected end (fields left out stay), or `resolve: true` to end it.
    """

    level: AnnouncementLevel | None = None
    components: list[StatusComponent] | None = Field(
        default=None, max_length=len(StatusComponent)
    )
    messages: list[AnnouncementMessageInput] | None = Field(
        default=None, min_length=1, max_length=MAX_ANNOUNCEMENT_LANGUAGES
    )
    expected_end_at: Microseconds | None = None
    resolve: IsAnnouncementResolution = False

    @model_validator(mode="after")
    def check_changes(self) -> Self:
        if self.messages is not None:
            check_messages(self.messages)
        if self.components is not None and len(set(self.components)) != len(
            self.components
        ):
            raise ValueError("Each component may appear only once.")
        if (
            self.level is None
            and self.components is None
            and self.messages is None
            and self.expected_end_at is None
            and not self.resolve
        ):
            raise ValueError("Nothing to change.")
        return self


class UpdateAnnouncementCommand(ImmutableDTO):
    user_id: UserId
    announcement_id: AnnouncementId
    body: UpdateAnnouncementBody
    client_ip_address: ClientIpAddress | None = None


class AnnouncementAdminView(ImmutableDTO):
    """One announcement with every translation, as the platform admin sees it."""

    id: AnnouncementId
    level: AnnouncementLevel
    status: AnnouncementStatus
    components: list[StatusComponent]
    messages: list[AnnouncementMessageInput]
    starts_at: Microseconds
    expected_end_at: Microseconds | None = None
    resolved_at: Microseconds | None = None
    created_by: UserId
    updated_by: UserId | None = None
    created_at: Microseconds
    updated_at: Microseconds


class AnnouncementsQuery(ImmutableDTO):
    """GET /v1/admin/announcements: one page, newest first."""

    user_id: UserId
    page: PageRequest


class AnnouncementPage(ImmutableDTO):
    items: list[AnnouncementAdminView]
    next_cursor: PageCursor | None = None
