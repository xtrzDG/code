from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.dto.admin import AdminClientQuery
from app.schemas.dto.client_story import ClientNoteList
from app.use_cases.admin.client_notes.client_note_board import ClientNoteBoard


class ListClientNotesUseCase(UseCaseContract[AdminClientQuery, ClientNoteList]):
    """
    GET /v1/admin/clients/{business_id}/notes: the platform team's notes
    about a client, pinned first, then the newest first, with their authors.
    """

    def __init__(self, board: ClientNoteBoard) -> None:
        self._board: ClientNoteBoard = board

    def run(self, input_data: AdminClientQuery) -> ClientNoteList:
        self._board.admit(
            input_data.user_id,
            input_data.business_id,
            PlatformAdminPermission.VIEW_CLIENTS,
        )
        return self._board.list(input_data.business_id)
