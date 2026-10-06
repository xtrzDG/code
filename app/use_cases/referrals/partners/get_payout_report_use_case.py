from app.contracts.repositories.referral_repositories import (
    CommissionEntryRepoContract,
    PartnerRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.access import PlatformAdminPermission
from app.schemas.constants.referrals import CommissionStatus
from app.schemas.domain.partners import PartnerDocument
from app.schemas.dto.referrals.commission_totals import CommissionTotal
from app.schemas.dto.referrals.partner_admin import (
    PayoutReportQuery,
    PayoutReportView,
    PayoutRowView,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.referrals.constrained_integers import CommissionInvoiceCount
from app.schemas.typings.referrals.prefixed_id import PartnerId
from app.use_cases.referrals.partners.partner_admin_gate import PartnerAdminGate


class GetPayoutReportUseCase(UseCaseContract[PayoutReportQuery, PayoutReportView]):
    """
    GET /v1/admin/partners/payouts?month=YYYY-MM (VIEW_CLIENTS): what each
    partner earned in the month (UTC), per currency: still to be paid out
    and paid, with how many invoices each. The database sums them; the
    rows go by partner name, then currency.
    """

    def __init__(
        self,
        gate: PartnerAdminGate,
        partner_repo: PartnerRepoContract,
        commission_entry_repo: CommissionEntryRepoContract,
    ) -> None:
        self._gate: PartnerAdminGate = gate
        self._partner_repo: PartnerRepoContract = partner_repo
        self._commissions: CommissionEntryRepoContract = commission_entry_repo

    def run(self, input_data: PayoutReportQuery) -> PayoutReportView:
        self._gate.admit(input_data.user_id, PlatformAdminPermission.VIEW_CLIENTS)
        totals: list[CommissionTotal] = self._commissions.totals_of_month(
            input_data.month
        )
        keys: list[tuple[PartnerId, CurrencyCode]] = list(
            dict.fromkeys((total.partner_id, total.currency_code) for total in totals)
        )
        partners: dict[PartnerId, PartnerDocument] = {
            partner.id: partner
            for partner in self._partner_repo.get_many(
                list(dict.fromkeys(partner_id for partner_id, _ in keys))
            )
        }
        rows: list[PayoutRowView] = [
            payout_row(partner_id, currency, totals, partners.get(partner_id))
            for partner_id, currency in keys
        ]
        rows.sort(key=lambda row: (str(row.partner_name or ""), str(row.currency_code)))
        return PayoutReportView(month=input_data.month, rows=rows)


def payout_row(
    partner_id: PartnerId,
    currency: CurrencyCode,
    totals: list[CommissionTotal],
    partner: PartnerDocument | None,
) -> PayoutRowView:
    def of(status: CommissionStatus) -> tuple[int, int]:
        amount: int = 0
        count: int = 0
        for total in totals:
            if (total.partner_id, total.currency_code, total.status) == (
                partner_id,
                currency,
                status,
            ):
                amount += int(total.amount_minor)
                count += int(total.invoice_count)
        return amount, count

    accrued_minor, accrued_invoices = of(CommissionStatus.ACCRUED)
    paid_minor, paid_invoices = of(CommissionStatus.PAID)
    return PayoutRowView(
        partner_id=partner_id,
        partner_name=None if partner is None else partner.name,
        currency_code=currency,
        accrued_minor=MoneyAmountMinor(accrued_minor),
        accrued_invoices=CommissionInvoiceCount(accrued_invoices),
        paid_minor=MoneyAmountMinor(paid_minor),
        paid_invoices=CommissionInvoiceCount(paid_invoices),
    )
