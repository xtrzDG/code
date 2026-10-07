import logging

from app.contracts.facilitators import ManagerNotificationFacilitatorContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.use_cases.admin.incidents.incident_notices import compose_breach_notice
from app.use_cases.shared.owner_contacts import contact_of

logger: logging.Logger = logging.getLogger(__name__)


class OwnerBreachNotices:
    """
    Sends a breach notice to every owner of one affected business through
    the outbox (retries, delivery state, the staff providers): by e-mail to
    the owner's sign-in address, else by SMS to the sign-in phone, in the
    owner's cabinet language. Each owner gets one notice per incident (the
    outbox ids derive from the incident), so sending again is harmless.
    Staff are not told: the DPA's notice goes to the Client, the owner.
    """

    def __init__(
        self,
        user_repo: UserRepoContract,
        manager_notifier: ManagerNotificationFacilitatorContract,
    ) -> None:
        self._user_repo: UserRepoContract = user_repo
        self._manager_notifier: ManagerNotificationFacilitatorContract = (
            manager_notifier
        )

    def send(self, incident: IncidentDocument, business: BusinessDocument) -> int:
        """How many owners' notices were queued."""

        subject = StaffAlertSubject(f"incident:{incident.id}")
        queued: int = 0
        for member in business.members:
            if member.role is not BusinessMemberRole.OWNER:
                continue

            owner: UserDocument | None = self._user_repo.get(member.user_id)
            contact: ManagerContact | None = (
                None if owner is None else contact_of(owner)
            )
            if contact is None:
                logger.warning(
                    "An owner of %s has no address for the breach notice of %s",
                    business.id,
                    incident.id,
                )
                continue

            queued += int(
                self._manager_notifier.notify(
                    StaffNotification(
                        business_id=business.id,
                        contact=contact,
                        text=compose_breach_notice(
                            incident, business, contact.language
                        ),
                        subject=subject,
                    )
                )
            )

        return queued
