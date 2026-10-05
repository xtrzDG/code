from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.client_care_repositories import ClientNoteRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.dto.client_story import ClientNoteList, UpdateClientNoteCommand
from app.use_cases.admin.client_notes.client_note_board import ClientNoteBoard


class UpdateClientNoteUseCase(
    UseCaseContract[UpdateClientNoteCommand, ClientNoteList]
):
    """
    PATCH /v1/admin/clients/{business_id}/notes/{note_id}: new words for a
    note, or pinned to the top (or not); what is left out stays.

    Raises:
        NotFoundError: the client has no such note.
    """

    def __init__(
        self,
        board: ClientNoteBoard,
        client_note_repo: ClientNoteRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._board: ClientNoteBoard = board
        self._client_note_repo: ClientNoteRepoContract = client_note_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateClientNoteCommand) -> ClientNoteList:
        self._board.admit(
            input_data.user_id,
            input_data.business_id,
            PlatformAdminPermission.WRITE_CLIENT_NOTES,
        )
        note: ClientNoteDocument = self._board.require_note(
            input_data.business_id, input_data.note_id
        )
        if input_data.body.text is not None:
            note.text = input_data.body.text

        if input_data.body.is_pinned is not None:
            note.is_pinned = input_data.body.is_pinned

        note.updated_at = self._wall_clock.now_unix()
        self._client_note_repo.save(note)
        return self._board.list(input_data.business_id)
