"""
The suppression list of customers who said STOP (kept through erasure) and
the signed links of full business exports.
"""

from collections.abc import Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.utility_contract import UtilityContract
from app.schemas.dto.privacy.suppression import SuppressedIdentity
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.booleans import IsMessagingSuppressed
from app.schemas.typings.privacy.constrained_integers import SuppressedIdentityCount
from app.schemas.typings.privacy.constrained_strings import BusinessExportToken
from app.schemas.typings.privacy.prefixed_id import BusinessExportId


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


class BusinessExportLinkSignerContract(UtilityContract, Protocol):
    def sign(
        self,
        business_id: BusinessId,
        export_id: BusinessExportId,
        expires_at: Microseconds,
    ) -> BusinessExportToken:
        """The token of the export's download link, valid until `expires_at`."""
        raise NotImplementedError

    def expiry_of(
        self,
        business_id: BusinessId,
        export_id: BusinessExportId,
        token: BusinessExportToken,
    ) -> Microseconds | None:
        """
        When a token of this export stops working; None when the platform
        did not sign it for this export (any key of the ring).
        """
        raise NotImplementedError
