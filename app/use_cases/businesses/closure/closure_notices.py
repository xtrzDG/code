"""Telling a business's owners that it closed, or that the closure was cancelled."""

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.business_closures import ClosureNoticeKind
from app.schemas.domain.business_closures import BusinessClosureDocument
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.users import UserDocument
from app.schemas.dto.business_closures.closure_notices import ClosureNotice
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.users.strings import UserDisplayName
from app.use_cases.shared.owner_contacts import owner_contacts


class ClosureNotices:
    """
    Every owner (at the sign-in e-mail, else by SMS, in their cabinet
    language) learns that the business closed, until when its data stays
    and how to keep it, or that the closure was cancelled. Each notice is
    queued once per owner and closure, so a retried request tells nobody
    twice; a failed delivery never fails the closure.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
        notice_transformer: TransformerContract[ClosureNotice, MessageText],
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )
        self._notice_transformer: TransformerContract[ClosureNotice, MessageText] = (
            notice_transformer
        )

    def send(
        self,
        business: BusinessDocument,
        closure: BusinessClosureDocument,
        kind: ClosureNoticeKind,
        actor_id: UserId | None,
    ) -> int:
        actor_name: UserDisplayName | None = self._name_of(actor_id)
        subject = StaffAlertSubject(
            f"business_closure:{kind.value}:{int(closure.requested_at)}"
        )
        contacts: list[ManagerContact] = owner_contacts(business, self._user_repo)
        return sum(
            int(
                self._manager_notifier.notify(
                    StaffNotification(
                        business_id=business.id,
                        contact=contact,
                        subject=subject,
                        text=self._notice_transformer.transform(
                            ClosureNotice(
                                kind=kind,
                                business_name=business.name,
                                actor_name=actor_name,
                                delete_after=closure.delete_after,
                                timezone=business.timezone,
                                language=contact.language,
                            )
                        ),
                    )
                )
            )
            for contact in contacts
        )

    def _name_of(self, user_id: UserId | None) -> UserDisplayName | None:
        if user_id is None:
            return None

        user: UserDocument | None = self._user_repo.get(user_id)
        if user is None:
            return None

        return user.display_name or UserDisplayName(
            str(user.email or user.phone_number or "")
        )
