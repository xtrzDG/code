from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.repositories.setup_repositories import (
    ActivationEventRepoContract,
    AssistantApplyRepoContract,
    SetupStateRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.constants.setup import ActivationEventKind
from app.schemas.domain.setup import (
    ActivationEventDocument,
    AssistantApplyDocument,
    SetupStateDocument,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.setup.setup_keys import (
    derive_activation_event_id,
    derive_assistant_apply_id,
    derive_setup_state_id,
)


class ActivationEventRepository(
    BusinessScopedRepository[ActivationEventDocument],
    ActivationEventRepoContract,
):
    """Milestones keyed by their derived id: one per business and kind."""

    def record_once(self, event: ActivationEventDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(event.id), event))

    def list_by_business(self, business_id: BusinessId) -> list[ActivationEventDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda event: (event.occurred_at, event.kind.value),
        )

    def mark_celebrated(
        self,
        business_id: BusinessId,
        kind: ActivationEventKind,
        celebrated_at: Microseconds,
    ) -> ActivationEventDocument | None:
        key: str = str(derive_activation_event_id(business_id, kind))

        def celebrate(
            stored: ActivationEventDocument,
        ) -> ActivationEventDocument | None:
            if stored.celebrated_at is not None:
                return None

            stored.celebrated_at = celebrated_at
            stored.updated_at = celebrated_at
            return stored

        changed: ActivationEventDocument | None = self._modify_in_business(
            business_id, key, celebrate
        )
        return changed or self._load(business_id, key)


class SetupStateRepository(
    BusinessScopedRepository[SetupStateDocument],
    SetupStateRepoContract,
):
    """One setup state per business, keyed by its derived id."""

    def get_by_business(self, business_id: BusinessId) -> SetupStateDocument | None:
        return self._load(business_id, str(derive_setup_state_id(business_id)))

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[SetupStateDocument], None],
        now: Microseconds,
    ) -> SetupStateDocument:
        state_id = derive_setup_state_id(business_id)
        self._collection.insert_if_absent(
            str(state_id),
            SetupStateDocument(
                id=state_id,
                business_id=business_id,
                created_at=now,
                updated_at=now,
            ),
        )

        def change_state(stored: SetupStateDocument) -> SetupStateDocument:
            apply(stored)
            stored.updated_at = now
            return stored

        changed: SetupStateDocument | None = self._modify_in_business(
            business_id, str(state_id), change_state
        )
        if changed is None:
            raise NotFoundError(f"The setup state of business {business_id} is gone.")

        return changed


class AssistantApplyRepository(
    BusinessScopedRepository[AssistantApplyDocument],
    AssistantApplyRepoContract,
):
    """The current apply of each business, keyed by its derived id."""

    def get_by_business(self, business_id: BusinessId) -> AssistantApplyDocument | None:
        return self._load(business_id, str(derive_assistant_apply_id(business_id)))

    def save(self, apply: AssistantApplyDocument) -> None:
        self._store(str(apply.id), apply)

    def modify(
        self,
        business_id: BusinessId,
        change: Callable[[AssistantApplyDocument], AssistantApplyDocument | None],
    ) -> AssistantApplyDocument | None:
        return self._modify_in_business(
            business_id, str(derive_assistant_apply_id(business_id)), change
        )

