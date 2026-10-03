"""Saving and reading saved replies in the inbox tests."""

from app.schemas.dto.inbox.quick_replies import (
    QuickReplyRequest,
    QuickReplyView,
    SaveQuickReplyCommand,
)
from app.schemas.typings.inbox.prefixed_id import QuickReplyId
from app.schemas.typings.users.prefixed_id import UserId
from tests.inbox.inbox_world import InboxWorld

HOURS_VARIANTS: list[dict[str, str]] = [
    {"language": "en", "text": "Hello {name}! We are open 9:00-23:00."},
    {"language": "ka", "text": "გამარჯობა, {name}! ღია ვართ 9:00-23:00."},
    {"language": "ru", "text": "Здравствуйте, {name}! Мы открыты с 9:00 до 23:00."},
]


def reply_request(
    shortcut: str = "hours",
    title: str = "Opening hours",
    variants: list[dict[str, str]] | None = None,
) -> QuickReplyRequest:
    return QuickReplyRequest.model_validate(
        {
            "shortcut": shortcut,
            "title": title,
            "variants": HOURS_VARIANTS if variants is None else variants,
        }
    )


def save(
    world: InboxWorld,
    request: QuickReplyRequest,
    caller: UserId | None = None,
    replacing: QuickReplyId | None = None,
) -> QuickReplyView:
    return world.save_quick_reply().run(
        SaveQuickReplyCommand(
            user_id=caller or world.owner.id,
            business_id=world.business.id,
            quick_reply_id=replacing,
            request=request,
        )
    )
