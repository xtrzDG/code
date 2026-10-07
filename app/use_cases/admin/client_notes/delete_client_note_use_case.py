from app.contracts.repositories.client_care_repositories import ClientNoteRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.dto.client_story import DeleteClientNoteCommand
from app.use_cases.admin.client_notes.client_note_board import ClientNoteBoard


class DeleteClientNoteUseCase(UseCaseContract[DeleteClientNoteCommand, None]):
    """
    DELETE /v1/admin/clients/{business_id}/notes/{note_id} (204).

    Raises:
        NotFoundError: the client has no such note.
    """

    def __init__(
        self, board: ClientNoteBoard, client_note_repo: ClientNoteRepoContract
    ) -> None:
        self._board: ClientNoteBoard = board
        self._client_note_repo: ClientNoteRepoContract = client_note_repo

    def run(self, input_data: DeleteClientNoteCommand) -> None:
        self._board.admit(
            input_data.user_id,
            input_data.business_id,
            PlatformAdminPermission.WRITE_CLIENT_NOTES,
        )
        self._board.require_note(input_data.business_id, input_data.note_id)
        self._client_note_repo.delete(input_data.business_id, input_data.note_id)
