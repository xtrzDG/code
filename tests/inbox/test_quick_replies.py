"""Saved replies: owners keep them, the whole team reads them."""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.inbox import QuickReplyVariable
from app.schemas.dto.inbox.quick_replies import (
    DeleteQuickReplyCommand,
    QuickRepliesQuery,
    QuickReplyList,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.inbox.prefixed_id import QuickReplyId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.inbox.quick_replies.quick_reply_views import MAX_QUICK_REPLIES
from tests.inbox.inbox_world import InboxWorld
from tests.inbox.quick_reply_steps import reply_request, save


def listed(world: InboxWorld, viewer: UserId) -> QuickReplyList:
    return world.list_quick_replies().run(
        QuickRepliesQuery(user_id=viewer, business_id=world.business.id)
    )


def codes(error: ApplicationError) -> list[str]:
    return [str(reason.code) for reason in error.reasons]


def test_owners_save_replies_and_staff_read_them_in_order() -> None:
    world = InboxWorld()
    hours = save(world, reply_request())
    world.later(1)
    save(
        world,
        reply_request(
            "address", "Where we are", [{"language": "en", "text": "Rustaveli 12."}]
        ),
    )

    replies = listed(world, world.staff.id).items

    assert [str(reply.shortcut) for reply in replies] == ["hours", "address"]
    assert replies[0] == hours
    assert hours.variables == [QuickReplyVariable.NAME]
    assert [str(variant.language) for variant in hours.variants] == ["en", "ka", "ru"]
    assert hours.created_by == world.owner.id


def test_replacing_keeps_the_place_author_and_creation() -> None:
    world = InboxWorld()
    first = save(world, reply_request())
    second = save(world, reply_request("menu", "Menu"))
    world.later(5)

    replaced = save(
        world,
        reply_request(
            "hours", "Hours", [{"language": "en", "text": "9-23, {business_name}"}]
        ),
        replacing=first.id,
    )

    assert [reply.id for reply in listed(world, world.owner.id).items] == [
        first.id,
        second.id,
    ]
    assert str(replaced.title) == "Hours"
    assert replaced.variables == [QuickReplyVariable.BUSINESS_NAME]
    assert replaced.updated_at == world.now
    actions = [(entry.action, str(entry.entity)) for entry in world.audit_entries()]
    assert actions[-1] == (AuditAction.UPDATE, "quick_reply")


def test_a_shortcut_belongs_to_one_reply_whatever_its_case() -> None:
    world = InboxWorld()
    first = save(world, reply_request("Hours"))

    with pytest.raises(ConflictError) as refused:
        save(world, reply_request("hours"))

    assert codes(refused.value) == ["shortcut_taken"]
    save(world, reply_request("HOURS"), replacing=first.id)


def test_texts_name_only_variables_the_inbox_fills_once_per_language() -> None:
    world = InboxWorld()

    with pytest.raises(ValidationFailedError) as unknown:
        save(
            world,
            reply_request(
                variants=[{"language": "en", "text": "Hi {first_name}, {_x} {name}"}]
            ),
        )
    with pytest.raises(ValidationFailedError) as twice:
        save(
            world,
            reply_request(
                variants=[
                    {"language": "en", "text": "One"},
                    {"language": "en", "text": "Two"},
                ]
            ),
        )

    assert codes(unknown.value) == ["unknown_variable"]
    assert [str(detail) for detail in unknown.value.reasons[0].details] == [
        "first_name",
        "x",
    ]
    assert codes(twice.value) == ["duplicate_language"]
    assert listed(world, world.owner.id).items == []


def test_a_business_keeps_at_most_a_hundred_replies() -> None:
    world = InboxWorld()
    for number in range(MAX_QUICK_REPLIES):
        save(world, reply_request(f"r{number}"))

    with pytest.raises(ConflictError) as refused:
        save(world, reply_request("one-more"))

    assert codes(refused.value) == ["too_many_quick_replies"]


def test_only_owners_change_replies() -> None:
    world = InboxWorld()
    reply = save(world, reply_request())

    with pytest.raises(AccessDeniedError):
        save(world, reply_request("menu"), caller=world.staff.id)
    with pytest.raises(AccessDeniedError):
        world.delete_quick_reply().run(
            DeleteQuickReplyCommand(
                user_id=world.staff.id,
                business_id=world.business.id,
                quick_reply_id=reply.id,
            )
        )


def test_deleting_answers_the_rest_and_unknown_replies_are_not_found() -> None:
    world = InboxWorld()
    hours = save(world, reply_request())
    menu = save(world, reply_request("menu", "Menu"))

    rest = world.delete_quick_reply().run(
        DeleteQuickReplyCommand(
            user_id=world.owner.id,
            business_id=world.business.id,
            quick_reply_id=hours.id,
        )
    )

    assert [reply.id for reply in rest.items] == [menu.id]
    with pytest.raises(NotFoundError):
        world.delete_quick_reply().run(
            DeleteQuickReplyCommand(
                user_id=world.owner.id,
                business_id=world.business.id,
                quick_reply_id=hours.id,
            )
        )
    with pytest.raises(NotFoundError):
        save(world, reply_request("new"), replacing=QuickReplyId())


def test_a_business_without_replies_lists_none_and_cannot_replace_one() -> None:
    world = InboxWorld()

    assert listed(world, world.staff.id).items == []
    with pytest.raises(NotFoundError):
        save(world, reply_request(), replacing=QuickReplyId())
    with pytest.raises(NotFoundError):
        world.delete_quick_reply().run(
            DeleteQuickReplyCommand(
                user_id=world.owner.id,
                business_id=world.business.id,
                quick_reply_id=QuickReplyId(),
            )
        )
