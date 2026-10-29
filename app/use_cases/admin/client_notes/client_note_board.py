"""
What the notes use cases share: the admin's permission check, the client's
business, and the notes as the client page shows them.
"""

from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.client_care_repositories import ClientNoteRepoContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.client_story import ClientNoteList, ClientNoteView
from app.schemas.dto.platform_admins import PlatformAdminAccessRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.client_health.prefixed_id import ClientNoteId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.shared.business_access import require_business

# The page shows every note of a client; a client gets a few a month.
MAX_CLIENT_NOTES: DocumentQueryLimit = DocumentQueryLimit(200)


class ClientNoteBoard:
    """
    The platform team's notes about one client: reading needs the client
    list (every admin role), writing needs WRITE_CLIENT_NOTES (SUPER and
    BILLING; support reads only). A note of another business is not found.
    """

    def __init__(
        self,
        authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ],
        business_repo: BusinessRepoContract,
        client_note_repo: ClientNoteRepoContract,
        user_repo: UserRepoContract,
    ) -> None:
        self._authorize_platform_admin: UseCaseContract[
            PlatformAdminAccessRequest, UserDocument
        ] = authorize_platform_admin
        self._business_repo: BusinessRepoContract = business_repo
        self._client_note_repo: ClientNoteRepoContract = client_note_repo
        self._user_repo: UserRepoContract = user_repo

    def admit(
        self,
        user_id: UserId,
        business_id: BusinessId,
        permission: PlatformAdminPermission,
    ) -> UserDocument:
        admin: UserDocument = self._authorize_platform_admin.run(
            PlatformAdminAccessRequest(user_id=user_id, permission=permission)
        )
        require_business(self._business_repo, business_id)
        return admin

    def require_note(
        self, business_id: BusinessId, note_id: ClientNoteId
    ) -> ClientNoteDocument:
        note: ClientNoteDocument | None = self._client_note_repo.get(
            business_id, note_id
        )
        if note is None:
            raise NotFoundError(f"Note {note_id} was not found.")

        return note

    def list(self, business_id: BusinessId) -> ClientNoteList:
        notes: list[ClientNoteDocument] = self._client_note_repo.list_by_business(
            business_id, MAX_CLIENT_NOTES
        )
        authors: dict[UserId, UserDocument] = {
            user.id: user
            for user in self._user_repo.get_many(
                sorted({note.author_user_id for note in notes}, key=str)
            )
        }
        ordered: list[ClientNoteDocument] = sorted(
            notes,
            key=lambda note: (not note.is_pinned, -int(note.created_at), str(note.id)),
        )
        return ClientNoteList(
            items=[
                ClientNoteView(
                    id=note.id,
                    text=note.text,
                    is_pinned=note.is_pinned,
                    author_user_id=note.author_user_id,
                    author_name=(
                        None
                        if note.author_user_id not in authors
                        else authors[note.author_user_id].display_name
                    ),
                    created_at=note.created_at,
                    updated_at=note.updated_at,
                )
                for note in ordered
            ]
        )
