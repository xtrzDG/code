from collections import Counter

from typed_time_provider import Microseconds

from app.contracts.repositories.referral_repositories import (
    CommissionEntryRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.referrals import CommissionStatus
from app.schemas.domain.partners import PartnerDocument
from app.schemas.domain.referrals import CommissionEntryDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.referrals.partner_admin import (
    MarkPayoutPaidCommand,
    PayoutReceipt,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.referrals.constrained_integers import CommissionInvoiceCount
from app.use_cases.referrals.partners.partner_admin_gate import (
    PARTNER_PAYOUT_ENTITY,
    PartnerAdminGate,
)


class MarkPayoutPaidUseCase(UseCaseContract[MarkPayoutPaidCommand, PayoutReceipt]):
    """
    POST /v1/admin/partners/{partner_id}/payouts (MANAGE_CLIENT_BILLING):
    the platform team paid a partner their commissions of a month: every
    commission of the month still to be paid becomes PAID, with when, by
    whom and the transfer's reference. Nothing to pay answers 409. Audited
    (UPDATE partner_payout, with how many commissions).
    """

    def __init__(
        self,
        gate: PartnerAdminGate,
        commission_entry_repo: CommissionEntryRepoContract,
    ) -> None:
        self._gate: PartnerAdminGate = gate
        self._commissions: CommissionEntryRepoContract = commission_entry_repo

    def run(self, input_data: MarkPayoutPaidCommand) -> PayoutReceipt:
        admin: UserDocument = self._gate.admit(
            input_data.user_id, PlatformAdminPermission.MANAGE_CLIENT_BILLING
        )
        partner: PartnerDocument = self._gate.require_partner(input_data.partner_id)
        entries: list[CommissionEntryDocument] = self._commissions.list_of_month(
            partner.id, input_data.request.month, CommissionStatus.ACCRUED
        )
        if entries == []:
            raise ConflictError("This partner has nothing to be paid for that month.")

        now: Microseconds = self._gate.now()
        sums: Counter[CurrencyCode] = Counter()
        for entry in entries:
            entry.status = CommissionStatus.PAID
            entry.paid_at = now
            entry.paid_by = admin.id
            entry.payout_reference = input_data.request.reference
            entry.updated_at = now
            self._commissions.save(entry)
            sums[entry.currency_code] += int(entry.amount_minor)

        self._gate.record(
            admin,
            AuditAction.UPDATE,
            PARTNER_PAYOUT_ENTITY,
            partner.id,
            input_data.client_ip_address,
            record_count=len(entries),
        )
        return PayoutReceipt(
            partner_id=partner.id,
            month=input_data.request.month,
            paid_invoices=CommissionInvoiceCount(len(entries)),
            amounts=[
                Money(amount_minor=MoneyAmountMinor(amount), currency_code=currency)
                for currency, amount in sorted(
                    sums.items(), key=lambda item: str(item[0])
                )
            ],
        )
