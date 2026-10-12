"""
The checks of the audit log's alert rules (`audit_alert_rules.py`): the
last hour's audit entries grouped by the database, and the latest checks
of the hash chains. Each figure is the worst group's; the detail names it
by an id only (a business, an admin, a destination digest), never a
person's contact or a customer.
"""

from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.repositories.audit_chain_repositories import (
    AuditActivityRepoContract,
    AuditChainRepoContract,
)
from app.schemas.constants.compliance import AuditAction, AuditChainStatus
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.admin.alerts.alert_checks import AlertCheck, observe

MICROSECONDS_PER_MINUTE: int = 60 * 1_000_000
BROKEN_NAMED: DocumentQueryLimit = DocumentQueryLimit(5)
# What a platform admin does inside a client's account: each such entry is
# in that client's own log, with the admin as its actor.
ADMIN_TENANT_ACTIONS: tuple[AuditAction, ...] = (
    AuditAction.ADMIN_ACCESS,
    AuditAction.SUPPORT_ACCESS_START,
    AuditAction.ADMIN_TRIAL_EXTENDED,
    AuditAction.ADMIN_DISCOUNT_GIVEN,
    AuditAction.ADMIN_CREDIT_GRANTED,
    AuditAction.ADMIN_SETUP_FEE_WAIVED,
    AuditAction.ADMIN_INVOICE_MARKED_PAID,
    AuditAction.ADMIN_PLAN_OVERRIDDEN,
)


class AuditAlertChecks:
    """The four checks, by alert code (`checks`)."""

    def __init__(
        self,
        audit_activity_repo: AuditActivityRepoContract,
        audit_chain_repo: AuditChainRepoContract,
    ) -> None:
        self._activity: AuditActivityRepoContract = audit_activity_repo
        self._chains: AuditChainRepoContract = audit_chain_repo

    def checks(self) -> Mapping[PlatformAlertCode, AlertCheck]:
        return {
            PlatformAlertCode.BULK_PERSONAL_DATA: self.bulk_personal_data,
            PlatformAlertCode.TENANT_HOPPING: self.tenant_hopping,
            PlatformAlertCode.FAILED_SIGN_IN_CHECKS: self.failed_sign_in_checks,
            PlatformAlertCode.AUDIT_CHAIN_BROKEN: self.audit_chain_broken,
        }

    def bulk_personal_data(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        counts = self._activity.count_personal_data_operations(window_start(rule, now))
        if not counts:
            return observe(rule, 0, "No exports or erasures in the last hour.")

        busiest = max(counts, key=lambda count: int(count.operation_count))
        figure: int = int(busiest.operation_count)
        return observe(
            rule,
            figure,
            f"Business {busiest.business_id} exported or erased personal data "
            f"{figure} times in the last hour.",
        )

    def tenant_hopping(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        counts = self._activity.count_tenants_by_admin(
            window_start(rule, now), ADMIN_TENANT_ACTIONS
        )
        if not counts:
            return observe(rule, 0, "No admin entered a client's account this hour.")

        widest = max(counts, key=lambda count: int(count.business_count))
        figure: int = int(widest.business_count)
        return observe(
            rule,
            figure,
            f"Admin {widest.actor_id} entered or changed {figure} clients' "
            "accounts in the last hour.",
        )

    def failed_sign_in_checks(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        counts = self._activity.count_failed_checks(window_start(rule, now))
        if not counts:
            return observe(rule, 0, "No failed sign-in checks in the last hour.")

        worst = max(counts, key=lambda count: int(count.failure_count))
        figure: int = int(worst.failure_count)
        return observe(
            rule,
            figure,
            f"{figure} failed sign-in checks in the last hour for one "
            f"destination ({worst.entity} {worst.entity_id}).",
        )

    def audit_chain_broken(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        broken: int = int(self._chains.count_by_status()[AuditChainStatus.BROKEN])
        if broken == 0:
            return observe(rule, 0, "Every audit chain checked is intact.")

        named: str = ", ".join(
            f"{status.id} at {status.broken_position} "
            f"({None if status.problem is None else status.problem.value})"
            for status in self._chains.list_broken(BROKEN_NAMED)
        )
        return observe(rule, broken, f"Broken audit chains: {broken} ({named}).")


def window_start(rule: PlatformAlertRule, now: Microseconds) -> Microseconds:
    """The start of the rule's window, ending now."""

    return Microseconds(int(now) - int(rule.window_minutes) * MICROSECONDS_PER_MINUTE)
