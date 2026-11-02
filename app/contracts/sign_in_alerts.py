"""Telling the platform team that sign-in codes are being sprayed."""

from typing import Protocol

from app.contracts.facilitator_contract import FacilitatorContract
from app.schemas.dto.sign_in_alerts import SignInCodeSprayAlert


class SignInCodeSprayAlertFacilitatorContract(FacilitatorContract, Protocol):
    def report_code_spray(self, alert: SignInCodeSprayAlert) -> None:
        """
        Tell the platform admins that one client network asks sign-in codes
        for many different phones and e-mails (a warning in the log, an
        error report and an e-mail to PLATFORM_ADMIN_EMAILS), at most once
        an hour per network. Never raises.
        """
        raise NotImplementedError
