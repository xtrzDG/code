"""
The suppression list of customers who said STOP (kept through erasure) and
the notice every owner gets when a full business export is downloaded.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.privacy.business_exports import ExportDownloadNotice
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.booleans import IsMessagingSuppressed
from app.schemas.typings.privacy.constrained_integers import SuppressedIdentityCount


class SuppressionListContract(FacilitatorContract, Protocol):
    """
    Whether a business may send a customer a message they did not ask for
    (a reminder, a text-back, a request for feedback). Identities are kept
    as HMAC digests only, so the list survives the customer's erasure.
    """

    def suppress(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
        now: Microseconds,
    ) -> SuppressedIdentityCount:
        """Add the identities (already listed ones stay); how many were new."""
        raise NotImplementedError

    def lift(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
    ) -> SuppressedIdentityCount:
        """Remove the identities (START); how many were listed."""
        raise NotImplementedError

    def is_suppressed(
        self,
        business_id: BusinessId,
        identities: Sequence[SuppressedIdentity],
    ) -> IsMessagingSuppressed:
        """True when any of the identities is on the business's list."""
        raise NotImplementedError


class ExportDownloadNoticeFacilitatorContract(FacilitatorContract, Protocol):
    def notice_download(
        self, business: BusinessDocument, notice: ExportDownloadNotice
    ) -> None:
        """
        Tell every owner of the business that its full export was
        downloaded: by whom, from which address and device. Never raises.
        """
        raise NotImplementedError
