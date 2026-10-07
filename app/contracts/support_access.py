"""Platform support's grants of access to a business, and sign-in notices."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.repo_contract import RepoContract
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.domain.users import UserDocument, UserSessionDocument
from app.schemas.dto.support_access import SupportAccessEnding
from app.schemas.typings.access.prefixed_id import SupportAccessGrantId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.users.prefixed_id import UserId


class SupportAccessGrantRepoContract(RepoContract, Protocol):
    """Grants of one business, read together with its id (indexed)."""

    def save(self, grant: SupportAccessGrantDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, grant_id: SupportAccessGrantId
    ) -> SupportAccessGrantDocument | None:
        raise NotImplementedError

    def list_open(self, business_id: BusinessId) -> list[SupportAccessGrantDocument]:
        """The business's OPEN grants (expired ones included until ended)."""
        raise NotImplementedError

    def list_open_of_admin(
        self, business_id: BusinessId, admin_user_id: UserId
    ) -> list[SupportAccessGrantDocument]:
        """One admin's OPEN looks into the business."""
        raise NotImplementedError

    def list_open_everywhere(self) -> list[SupportAccessGrantDocument]:
        """Every OPEN grant of every business (platform-wide, indexed)."""
        raise NotImplementedError

    def end(
        self,
        business_id: BusinessId,
        grant_id: SupportAccessGrantId,
        ended: SupportAccessEnding,
    ) -> SupportAccessGrantDocument | None:
        """
        End an OPEN grant in one atomic step (compare-and-swap on the
        status): the ended grant, or None when it is missing or another
        request ended it first.
        """
        raise NotImplementedError


class SignInNoticeFacilitatorContract(FacilitatorContract, Protocol):
    def notice_new_device(
        self,
        user: UserDocument,
        session: UserSessionDocument,
        other_sessions: Sequence[UserSessionDocument],
    ) -> None:
        """
        Tell the person about a sign-in from a device none of their other
        live sessions uses (their devices with notifications on and their
        sign-in e-mail), with a link to Account → Security. A first
        sign-in, or one from a known device, tells nobody. Never raises.
        """
        raise NotImplementedError
