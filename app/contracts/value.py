"""
Contracts of the value context: what a niche typically earns and saves,
and the delivery of the owners' digests and monthly reports.
"""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.registry_contract import RegistryContract
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.value.niche_value import NicheValueDefaults
from app.schemas.dto.value.value_reports import ValueReportView
from app.schemas.typings.value.constrained_integers import DigestRecipientCount


class NicheValueRegistryContract(RegistryContract, Protocol):
    def get(self, niche_key: NicheKey) -> NicheValueDefaults:
        """The estimates of a niche (every niche has them)."""
        raise NotImplementedError


class OwnerDigestFacilitatorContract(FacilitatorContract, Protocol):
    def send(
        self,
        business: BusinessDocument,
        report: ValueReportView,
    ) -> DigestRecipientCount:
        """
        Queue a stored digest or monthly report for every owner of the
        business who wants its kind: to their sign-in e-mail and their
        devices with notifications on, each in its own language, once per
        report and recipient (also when asked again). How many addresses
        and devices it was queued for; never raises.
        """
        raise NotImplementedError
