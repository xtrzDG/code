"""
The checks of the platform health alerts (LOG-04, LOG-05):

- `webhook_signature_failures`: refused webhook deliveries (unsigned,
  badly signed, stale), counted by the API processes;
- `storage_errors`: requests and jobs the database or the object storage
  failed, counted where the failure was answered or reported;
- `api_latency`: API requests slower than 2 s, against every request of
  the API availability slots of the same 30 minutes;
- `backup_failed`: the last recorded off-site backup failed, or the last
  success is older than the rule's window (no recorded backup at all, as
  in development and the preview stand, is quiet);
- `tenant_sms_volume`: SMS of a business past its hourly alert volume or
  refused past its cap (`TenantSmsVolumeGuardAdapter`);
- `otp_conversion`: login codes of the last hour that were never used,
  among those settled (used, or expired unused).
"""

from collections import Counter
from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.monitoring import (
    MaintenanceRunRepoContract,
    SignalCounterAdapterContract,
)
from app.contracts.repositories.user_repositories import OtpChallengeRepoContract
from app.contracts.service_levels import ServiceLevelSlotRepoContract
from app.schemas.constants.monitoring import (
    MaintenanceRunKind,
    MaintenanceRunOutcome,
    PlatformAlertCode,
    PlatformSignal,
)
from app.schemas.constants.telemetry import ServiceLevelSeries
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.users import OtpChallengeDocument
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.use_cases.admin.alerts.alert_checks import AlertCheck, observe, observe_rate
from app.use_cases.admin.alerts.alert_texts import describe_duration, describe_percent

MICROSECONDS_PER_SECOND: int = 1_000_000
MICROSECONDS_PER_MINUTE: int = 60 * MICROSECONDS_PER_SECOND
NAMED_COUNTRIES: int = 3
UNKNOWN_COUNTRY: str = "unknown"


class PlatformHealthAlertChecks:
    """The platform health checks, by alert code."""

    def __init__(
        self,
        signal_counter: SignalCounterAdapterContract,
        slot_repo: ServiceLevelSlotRepoContract,
        maintenance_run_repo: MaintenanceRunRepoContract,
        otp_challenge_repo: OtpChallengeRepoContract,
    ) -> None:
        self._signals: SignalCounterAdapterContract = signal_counter
        self._slots: ServiceLevelSlotRepoContract = slot_repo
        self._runs: MaintenanceRunRepoContract = maintenance_run_repo
        self._challenges: OtpChallengeRepoContract = otp_challenge_repo

    def checks(self) -> Mapping[PlatformAlertCode, AlertCheck]:
        return {
            PlatformAlertCode.WEBHOOK_SIGNATURE_FAILURES: self.webhook_failures,
            PlatformAlertCode.STORAGE_ERRORS: self.storage_errors,
            PlatformAlertCode.API_LATENCY: self.api_latency,
            PlatformAlertCode.BACKUP_FAILED: self.backup_failed,
            PlatformAlertCode.TENANT_SMS_VOLUME: self.tenant_sms_volume,
            PlatformAlertCode.OTP_CONVERSION: self.otp_conversion,
        }

    def webhook_failures(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        refused: int = self._recent(PlatformSignal.WEBHOOK_REFUSED, now)
        return observe(
            rule,
            refused,
            f"{refused} webhook deliveries were refused in the last "
            f"{recent_minutes(rule)} minutes; the app.security lines name each "
            "provider and reason.",
        )

    def storage_errors(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        database: int = self._recent(PlatformSignal.DATABASE_ERROR, now)
        objects: int = self._recent(PlatformSignal.OBJECT_STORAGE_ERROR, now)
        return observe(
            rule,
            database + objects,
            f"In the last {recent_minutes(rule)} minutes {database} requests or "
            f"jobs failed on the database and {objects} on the object storage.",
        )

    def api_latency(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        since = Microseconds(
            int(now) - int(rule.window_minutes) * MICROSECONDS_PER_MINUTE
        )
        requests: int = sum(
            int(slot.total)
            for slot in self._slots.list_window(
                ServiceLevelSeries.API_AVAILABILITY,
                since,
                Microseconds(int(now) + 1),
            )
        )
        slow: int = min(requests, self._recent(PlatformSignal.SLOW_API_REQUEST, now))
        return observe_rate(
            rule,
            slow,
            requests,
            f"{slow} of {requests} API requests took longer than 2 s in the last "
            f"{int(rule.window_minutes)} minutes ({describe_percent(slow, requests)}).",
        )

    def backup_failed(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        latest: MaintenanceRunDocument | None = self._runs.find_latest(
            MaintenanceRunKind.BACKUP
        )
        if latest is None:
            return observe(rule, 0, "No off-site backup has been recorded yet.")

        age: int = max(
            0, (int(now) - int(latest.finished_at)) // MICROSECONDS_PER_SECOND
        )
        if latest.outcome is MaintenanceRunOutcome.FAILED:
            return observe(
                rule,
                1,
                f"The last off-site backup failed {describe_duration(age)} ago: "
                f"{latest.error or 'no error recorded'}.",
            )

        is_stale: bool = age > int(rule.window_minutes) * 60
        return observe(
            rule,
            1 if is_stale else 0,
            f"The last off-site backup succeeded {describe_duration(age)} ago"
            + (": the daily backup job stopped." if is_stale else "."),
        )

    def tenant_sms_volume(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        surges: int = self._recent(PlatformSignal.TENANT_SMS_SURGE, now)
        return observe(
            rule,
            surges,
            f"{surges} times in the last {recent_minutes(rule)} minutes a "
            "business passed its hourly SMS volume or had an SMS refused at its "
            "cap; the warning lines of app.adapters name the business.",
        )

    def otp_conversion(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        since = Microseconds(
            int(now) - int(rule.window_minutes) * MICROSECONDS_PER_MINUTE
        )
        settled: list[OtpChallengeDocument] = [
            challenge
            for challenge in self._challenges.list_created_since(since)
            if challenge.is_consumed or int(challenge.expires_at) <= int(now)
        ]
        unused: list[OtpChallengeDocument] = [
            challenge for challenge in settled if not challenge.is_consumed
        ]
        return observe_rate(
            rule,
            len(unused),
            len(settled),
            f"{len(unused)} of {len(settled)} login codes of the last "
            f"{int(rule.window_minutes)} minutes were never used "
            f"({describe_percent(len(unused), len(settled))})"
            + describe_countries(unused),
        )

    def _recent(self, signal: PlatformSignal, now: Microseconds) -> int:
        tally = self._signals.read(signal, now)
        return int(tally.current) + int(tally.previous)


def recent_minutes(rule: PlatformAlertRule) -> str:
    """ "15-30": the signal windows a count covers."""

    return f"{int(rule.window_minutes)}-{2 * int(rule.window_minutes)}"


def describe_countries(unused: list[OtpChallengeDocument]) -> str:
    """ "; most to IT 12, GB 3." for the countries with the most unused codes."""

    counts: Counter[str] = Counter(
        UNKNOWN_COUNTRY
        if challenge.country_code is None
        else str(challenge.country_code)
        for challenge in unused
    )
    if not counts:
        return "."

    named: str = ", ".join(
        f"{country} {count}" for country, count in counts.most_common(NAMED_COUNTRIES)
    )
    return f"; most to {named}."
