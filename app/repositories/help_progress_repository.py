from collections.abc import Callable

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.help import HelpProgressRepoContract
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.typings.users.prefixed_id import UserId


class HelpProgressRepository(HelpProgressRepoContract):
    """
    One row per person, keyed by the user's id (a platform collection):
    what they have seen of the cabinet's guidance. A keyed read, never a
    scan.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[HelpProgressDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[HelpProgressDocument] = (
            collection
        )

    def find(self, user_id: UserId) -> HelpProgressDocument | None:
        return self._collection.get(str(user_id))

    def save(self, progress: HelpProgressDocument) -> None:
        self._collection.upsert(str(progress.user_id), progress)

    def change(
        self,
        user_id: UserId,
        change: Callable[[HelpProgressDocument], HelpProgressDocument | None],
        empty: HelpProgressDocument,
    ) -> HelpProgressDocument:
        """
        Apply `change` to the person's row in one step (a row lock), first
        storing `empty` when they have none, so two tabs closing different
        hints both count.
        """

        self._collection.insert_if_absent(str(user_id), empty)
        changed: HelpProgressDocument | None = self._collection.modify(
            str(user_id), change
        )
        if changed is not None:
            return changed

        stored: HelpProgressDocument | None = self._collection.get(str(user_id))
        return stored if stored is not None else empty
