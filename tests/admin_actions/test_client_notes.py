"""
The platform team's notes about a client: pinned first, then the newest;
SUPER and BILLING write, support only reads; another client's note is not
found.
"""

import pytest

from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.client_story import (
    ClientNoteBody,
    ClientNoteChange,
    ClientNoteList,
    CreateClientNoteCommand,
    DeleteClientNoteCommand,
    UpdateClientNoteCommand,
)
from app.schemas.exceptions.application_errors import AccessDeniedError, NotFoundError
from app.schemas.typings.client_health.constrained_strings import ClientNoteText
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.client_notes.create_client_note_use_case import (
    CreateClientNoteUseCase,
)
from app.use_cases.admin.client_notes.delete_client_note_use_case import (
    DeleteClientNoteUseCase,
)
from app.use_cases.admin.client_notes.list_client_notes_use_case import (
    ListClientNotesUseCase,
)
from app.use_cases.admin.client_notes.update_client_note_use_case import (
    UpdateClientNoteUseCase,
)
from tests.admin_actions.action_world import ActionWorld


def write(
    world: ActionWorld, author: UserId, text: str, is_pinned: bool = False
) -> ClientNoteList:
    return CreateClientNoteUseCase(
        world.note_board, world.note_repo, world.testbed.clock.wall_clock
    ).run(
        CreateClientNoteCommand(
            user_id=author,
            business_id=world.business.id,
            body=ClientNoteBody(text=ClientNoteText(text), is_pinned=is_pinned),
        )
    )


def read(world: ActionWorld, reader: UserId) -> ClientNoteList:
    return ListClientNotesUseCase(world.note_board).run(
        AdminClientQuery(user_id=reader, business_id=world.business.id)
    )


def test_notes_read_pinned_first_then_the_newest_with_their_authors() -> None:
    world = ActionWorld()
    write(world, world.founder.id, "Called the owner: menu photos next week")
    world.testbed.clock.advance(hours=1)
    write(world, world.accountant.id, "Pays by bank transfer", is_pinned=True)
    world.testbed.clock.advance(hours=1)
    write(world, world.founder.id, "Asked for a discount for a year")

    notes = read(world, world.support.id).items

    assert [str(note.text) for note in notes] == [
        "Pays by bank transfer",
        "Asked for a discount for a year",
        "Called the owner: menu photos next week",
    ]
    assert [str(note.author_name) for note in notes] == ["Levan", "Nino", "Nino"]


def test_a_note_is_pinned_reworded_and_deleted() -> None:
    world = ActionWorld()
    [note] = write(world, world.founder.id, "Prefers WhatsApp").items
    update = UpdateClientNoteUseCase(
        world.note_board, world.note_repo, world.testbed.clock.wall_clock
    )

    [changed] = update.run(
        UpdateClientNoteCommand(
            user_id=world.accountant.id,
            business_id=world.business.id,
            note_id=note.id,
            body=ClientNoteChange(is_pinned=True),
        )
    ).items
    [reworded] = update.run(
        UpdateClientNoteCommand(
            user_id=world.founder.id,
            business_id=world.business.id,
            note_id=note.id,
            body=ClientNoteChange(text=ClientNoteText("Prefers calls after 18:00")),
        )
    ).items
    DeleteClientNoteUseCase(world.note_board, world.note_repo).run(
        DeleteClientNoteCommand(
            user_id=world.founder.id, business_id=world.business.id, note_id=note.id
        )
    )

    assert changed.is_pinned
    assert (str(reworded.text), reworded.is_pinned) == (
        "Prefers calls after 18:00",
        True,
    )
    assert read(world, world.founder.id).items == []


def test_support_reads_notes_but_never_writes_them() -> None:
    world = ActionWorld()

    with pytest.raises(AccessDeniedError):
        write(world, world.support.id, "Support was here")

    assert read(world, world.support.id).items == []


def test_a_note_of_another_client_is_not_found() -> None:
    world = ActionWorld()
    other_owner = world.testbed.add_user(phone_number="+995599000777")
    other = world.testbed.add_business(other_owner, name="Other cafe")
    stranger = ClientNoteDocument(
        business_id=other.id,
        author_user_id=world.founder.id,
        text=ClientNoteText("Another client's note"),
    )
    world.note_repo.save(stranger)

    with pytest.raises(NotFoundError):
        DeleteClientNoteUseCase(world.note_board, world.note_repo).run(
            DeleteClientNoteCommand(
                user_id=world.founder.id,
                business_id=world.business.id,
                note_id=ClientNoteId(str(stranger.id)),
            )
        )

    assert world.note_repo.get(other.id, stranger.id) is not None
