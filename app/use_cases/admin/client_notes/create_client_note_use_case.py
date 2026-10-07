from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.client_care_repositories import ClientNoteRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.client_story import ClientNoteList, CreateClientNoteCommand
from app.use_cases.admin.client_notes.client_note_board import ClientNoteBoard


class CreateClientNoteUseCase(UseCaseContract[CreateClientNoteCommand, ClientNoteList]):
    """
    POST /v1/admin/clients/{business_id}/notes: a platform admin who may
    write notes (SUPER, BILLING) writes one down; the answer is the client's
    notes as the page shows them.
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

    def run(self, input_data: CreateClientNoteCommand) -> ClientNoteList:
        admin: UserDocument = self._board.admit(
            input_data.user_id,
            input_data.business_id,
            PlatformAdminPermission.WRITE_CLIENT_NOTES,
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._client_note_repo.save(
            ClientNoteDocument(
                business_id=input_data.business_id,
                author_user_id=admin.id,
                text=input_data.body.text,
                is_pinned=input_data.body.is_pinned,
                created_at=now,
                updated_at=now,
            )
        )
        return self._board.list(input_data.business_id)
