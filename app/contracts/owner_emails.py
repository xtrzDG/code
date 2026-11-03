"""Notices that reach every owner at the e-mail address of their account."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.notifications import StaffAlertTextsContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.notifications.staff_alerts import StaffAlert
from app.schemas.typings.handoffs.constrained_integers import (
    DeliveredNotificationCount,
)


class OwnerAccountEmailFacilitatorContract(FacilitatorContract, Protocol):
    def email_owners(
        self,
        business: BusinessDocument,
        alert: StaffAlert,
        texts: StaffAlertTextsContract,
    ) -> DeliveredNotificationCount:
        """
        E-mail the alert's brief, with a signed link to its page, to the
        account e-mail address of every owner of the business, each in the
        language of their account: an owner without a device or a staff
        contact still hears it. An address a staff contact of the business
        already gets the alert at is skipped (one e-mail per address).
        Returns how many were queued. Never raises.
        """
        raise NotImplementedError
